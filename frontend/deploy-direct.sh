#!/bin/bash

# Direct AWS Amplify Deployment without GitHub
set -e

echo "🚀 Direct AWS Amplify Deployment Starting..."

# Configuration
APP_NAME="dreamops-frontend"
BRANCH_NAME="main"
REGION="ap-south-1"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

# Build the app locally first
echo "📦 Building app locally..."
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi

pnpm install
pnpm build

# Create or get Amplify app
echo "📱 Setting up Amplify app..."
APP_ID=$(aws amplify list-apps --region $REGION --query "apps[?name=='$APP_NAME'].appId" --output text 2>/dev/null || echo "")

if [ -z "$APP_ID" ]; then
    echo "Creating new Amplify app..."
    APP_ID=$(aws amplify create-app \
        --name "$APP_NAME" \
        --platform "WEB_COMPUTE" \
        --region $REGION \
        --query 'app.appId' \
        --output text)
    
    # Create branch
    aws amplify create-branch \
        --app-id $APP_ID \
        --branch-name $BRANCH_NAME \
        --region $REGION
fi

echo "✅ App ID: $APP_ID"

# Create deployment archive
echo "📦 Creating deployment archive..."
cd .next
zip -r ../amplify-deploy.zip . -q
cd ..

# Upload to S3
BUCKET="amplify-${APP_ID}-${RANDOM}"
echo "☁️ Uploading to S3..."

aws s3 mb s3://$BUCKET --region $REGION
aws s3 cp amplify-deploy.zip s3://$BUCKET/ --region $REGION

# Get signed URL
URL=$(aws s3 presign s3://$BUCKET/amplify-deploy.zip --expires-in 3600 --region $REGION)

# Start deployment
echo "🚀 Starting deployment..."
JOB=$(aws amplify start-deployment \
    --app-id $APP_ID \
    --branch-name $BRANCH_NAME \
    --source-url "$URL" \
    --region $REGION \
    --output json)

JOB_ID=$(echo $JOB | jq -r '.jobSummary.jobId')
echo "Job ID: $JOB_ID"

# Monitor
echo "⏳ Waiting for deployment..."
while true; do
    STATUS=$(aws amplify get-job \
        --app-id $APP_ID \
        --branch-name $BRANCH_NAME \
        --job-id $JOB_ID \
        --region $REGION \
        --query 'job.summary.status' \
        --output text)
    
    echo "Status: $STATUS"
    
    if [ "$STATUS" = "SUCCEED" ]; then
        break
    elif [ "$STATUS" = "FAILED" ]; then
        echo "❌ Deployment failed"
        exit 1
    fi
    sleep 5
done

# Cleanup
rm amplify-deploy.zip
aws s3 rm s3://$BUCKET/amplify-deploy.zip
aws s3 rb s3://$BUCKET

# Get URL
DOMAIN=$(aws amplify get-app --app-id $APP_ID --region $REGION --query 'app.defaultDomain' --output text)
echo ""
echo "✅ Deployment complete!"
echo "🌐 App URL: https://${BRANCH_NAME}.${DOMAIN}"