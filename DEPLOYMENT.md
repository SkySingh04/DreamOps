# AWS Deployment Guide for Oncall Agent

This guide provides step-by-step instructions for deploying the Oncall Agent to AWS using Terraform and GitHub Actions.

## ⚠️ Security Notice

**NEVER** commit AWS credentials to version control. Use IAM roles and GitHub Secrets for secure deployments.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.5.0
- GitHub repository with Actions enabled
- Docker for local testing

## Architecture Overview

The deployment creates:
- **VPC** with public/private subnets across 2 AZs
- **ECS Fargate** cluster for the backend
- **Application Load Balancer** for backend API
- **S3 + CloudFront** for frontend hosting
- **ECR** for Docker image storage
- **CloudWatch** for monitoring and alarms
- **Secrets Manager** for sensitive configuration

## Step 1: Prepare AWS Secrets

1. Create secrets in AWS Secrets Manager:

```bash
# Store Anthropic API key
aws secretsmanager create-secret \
  --name oncall-agent/anthropic-api-key \
  --secret-string "YOUR_ANTHROPIC_API_KEY"

# Store Kubernetes config (if using K8s integration)
aws secretsmanager create-secret \
  --name oncall-agent/k8s-config \
  --secret-string file://~/.kube/config
```

2. Note the ARNs of created secrets for Terraform variables.

## Step 2: Configure GitHub Secrets

Add these secrets to your GitHub repository:

1. Go to Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `AWS_ACCESS_KEY_ID`: AWS access key for deployment
   - `AWS_SECRET_ACCESS_KEY`: AWS secret key
   - `CLOUDFRONT_DISTRIBUTION_ID`: (will be added after initial deployment)
   - `REACT_APP_API_URL`: (will be added after backend deployment)

## Step 3: Deploy Infrastructure with Terraform

1. Initialize Terraform:

```bash
cd infrastructure/terraform
terraform init
```

2. Create a `terraform.tfvars` file:

```hcl
project_name = "oncall-agent"
environment  = "production"
aws_region   = "us-east-1"

# Replace with your secret ARNs from Step 1
anthropic_api_key_arn = "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:oncall-agent/anthropic-api-key-XXXXX"
k8s_config_secret_arn = "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:oncall-agent/k8s-config-XXXXX"

alarm_email = "your-email@example.com"
```

3. Plan and apply:

```bash
terraform plan
terraform apply
```

4. Note the outputs:
   - `backend_api_url`: Add as `REACT_APP_API_URL` in GitHub Secrets
   - `cloudfront_distribution_id`: Add as `CLOUDFRONT_DISTRIBUTION_ID` in GitHub Secrets

## Step 4: Initial Backend Deployment

1. Build and push the initial Docker image:

```bash
cd backend

# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t oncall-agent-backend -f Dockerfile.prod .
docker tag oncall-agent-backend:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/oncall-agent-backend:latest

# Push
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/oncall-agent-backend:latest
```

2. Update ECS service to use the new image.

## Step 5: Deploy Frontend

The frontend will be automatically deployed when you push to the main branch, but for initial deployment:

```bash
cd frontend
npm install
npm run build

# Sync to S3
aws s3 sync build/ s3://oncall-agent-frontend-production --delete

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

## Step 6: Configure CI/CD

The GitHub Actions workflows are already configured in:
- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`

These will automatically:
1. Run tests and linting on pull requests
2. Deploy to AWS when merging to main branch

## Step 7: Verify Deployment

1. Check ECS service is running:
```bash
aws ecs describe-services \
  --cluster oncall-agent-cluster \
  --services oncall-agent-backend-service
```

2. Test the backend API:
```bash
curl http://YOUR_ALB_DNS_NAME/health
```

3. Access the frontend via CloudFront URL.

## Monitoring

1. **CloudWatch Dashboards**: View the created dashboard in AWS Console
2. **Alarms**: CPU and memory alarms will notify via email
3. **Logs**: Check CloudWatch Logs for application logs

## Updating the Application

### Backend Updates
1. Make code changes
2. Push to main branch
3. GitHub Actions will automatically build and deploy

### Frontend Updates
1. Make code changes
2. Push to main branch
3. GitHub Actions will automatically build and deploy

## Cost Optimization

To minimize AWS costs:
1. Use Fargate Spot for non-production environments
2. Set appropriate auto-scaling policies
3. Use S3 lifecycle policies for logs
4. Consider using AWS Lambda for the backend if load is intermittent

## Troubleshooting

### ECS Task Fails to Start
- Check CloudWatch Logs for the task
- Verify secrets are accessible
- Ensure Docker image is correctly built

### Frontend Not Loading
- Check CloudFront distribution status
- Verify S3 bucket policy
- Check browser console for CORS issues

### High AWS Costs
- Review CloudWatch metrics
- Check for unused resources
- Enable cost allocation tags

## Security Best Practices

1. **Never commit secrets** to version control
2. **Use IAM roles** instead of access keys where possible
3. **Enable MFA** for AWS accounts
4. **Regularly rotate** secrets and access keys
5. **Use VPC endpoints** for AWS services
6. **Enable GuardDuty** for threat detection

## Next Steps

1. Set up custom domain with Route 53
2. Add WAF rules for additional security
3. Implement blue/green deployments
4. Add API Gateway for rate limiting
5. Set up VPN for secure K8s cluster access