# AWS Amplify Deployment Guide

This guide will help you deploy the DreamOps frontend to AWS Amplify.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. GitHub repository connected to AWS Amplify

## Setup Steps

### 1. Create AWS Amplify App

```bash
# Create Amplify app
aws amplify create-app \
  --name "dreamops-frontend" \
  --repository "https://github.com/SkySingh04/DreamOps" \
  --access-token "YOUR_GITHUB_TOKEN" \
  --region ap-south-1
```

### 2. Connect GitHub Repository

1. Go to AWS Amplify Console
2. Click "Connect app" > "GitHub"
3. Authorize AWS Amplify to access your GitHub repository
4. Select the repository: `SkySingh04/DreamOps`
5. Select branch: `main`

### 3. Configure Build Settings

The `amplify.yml` file in the frontend directory already contains the build configuration:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm install -g pnpm
        - pnpm install
    build:
      commands:
        - pnpm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
      - .pnpm-store/**/*
```

### 4. Environment Variables

Add these environment variables in AWS Amplify Console:

```
NEXT_PUBLIC_API_URL=https://your-backend-api-url.com
POSTGRES_URL=postgresql://user:password@host:5432/database
```

### 5. GitHub Secrets

Add these secrets to your GitHub repository:

1. `AWS_ACCESS_KEY_ID` - AWS access key with Amplify permissions
2. `AWS_SECRET_ACCESS_KEY` - AWS secret key
3. `AMPLIFY_APP_ID` - Your Amplify app ID (found in Amplify Console)

### 6. Deploy

1. Push changes to the `main` branch
2. GitHub Actions will automatically trigger deployment
3. Monitor deployment in AWS Amplify Console

## Manual Deployment

If you need to deploy manually:

```bash
# Start deployment
aws amplify start-deployment \
  --app-id YOUR_APP_ID \
  --branch-name main

# Check deployment status
aws amplify get-job \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --job-id JOB_ID
```

## Benefits of AWS Amplify over S3/CloudFront

1. **Server-Side Rendering**: Full Next.js SSR support
2. **API Routes**: Backend API routes work out of the box
3. **Automatic SSL**: Free SSL certificates
4. **Git Integration**: Auto-deploy on push
5. **Preview Deployments**: Automatic preview URLs for pull requests
6. **Environment Variables**: Easy environment management
7. **Monitoring**: Built-in CloudWatch integration
8. **Rollback**: Easy rollback to previous versions

## Monitoring

Access your app at: `https://main.YOUR_APP_ID.amplifyapp.com`

Check deployment logs in:
- AWS Amplify Console
- CloudWatch Logs
- GitHub Actions logs

## Troubleshooting

### Build Failures

1. Check `amplify.yml` configuration
2. Verify all environment variables are set
3. Check build logs in Amplify Console

### 404 Errors

Ensure your Amplify app has proper redirect rules for Next.js:

```json
[
  {
    "source": "/<*>",
    "target": "/index.html",
    "status": "404-200",
    "condition": null
  }
]
```

### Environment Variables

- Build-time variables: `NEXT_PUBLIC_*`
- Runtime variables: Set in Amplify Console