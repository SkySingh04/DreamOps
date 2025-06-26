# Deployment Guide

This guide covers all deployment options for DreamOps, including AWS Terraform infrastructure and AWS Amplify for the frontend.

## Overview

DreamOps supports multiple deployment strategies:
- **Full AWS Deployment**: Terraform infrastructure with ECS, CloudFront, and load balancers
- **AWS Amplify**: Simplified frontend deployment with automatic CI/CD
- **Hybrid Approach**: Amplify frontend with custom backend infrastructure

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI installed and configured
- Terraform >= 1.5.0 (for infrastructure deployment)
- Node.js and npm (for frontend deployment)
- Docker (for containerized deployment)

## Option 1: Terraform Infrastructure (Recommended)

### Full Infrastructure Deployment

This option deploys the complete infrastructure including backend and frontend.

#### 1. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Key, Region, and Output format
```

#### 2. Deploy Infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

#### Infrastructure Components

The Terraform deployment creates:
- **VPC** with public/private subnets across 2 AZs
- **ECS Fargate** cluster for the backend
- **Application Load Balancer** for backend API
- **S3 + CloudFront** for frontend hosting
- **ECR** for Docker image storage
- **CloudWatch** for monitoring and alarms
- **Secrets Manager** for sensitive configuration

#### 3. Deploy Applications

**Backend Deployment:**
```bash
# Build and push Docker image
cd backend
docker build -t oncall-agent -f Dockerfile.prod .
docker tag oncall-agent:latest $ECR_REGISTRY/oncall-agent:latest
docker push $ECR_REGISTRY/oncall-agent:latest

# Deploy via GitHub Actions (automatic on push to main)
git push origin main
```

**Frontend Deployment:**
```bash
cd frontend
npm run build

# Deploy to S3
aws s3 sync dist/ s3://your-bucket-name

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

## Option 2: AWS Amplify (Frontend Only)

### Quick AWS CLI Setup

```bash
# Create Amplify App
aws amplify create-app \
  --name "dreamops-frontend" \
  --repository "https://github.com/yourusername/oncall-agent" \
  --platform "WEB_COMPUTE" \
  --region ap-south-1

# Note the App ID from the output
APP_ID="your-app-id"

# Update app with build spec
cat > amplify.yml << 'EOF'
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - npm install -g pnpm
            - pnpm install
        build:
          commands:
            - pnpm run build
      artifacts:
        baseDirectory: frontend/.next
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
    appRoot: .
EOF

aws amplify update-app \
  --app-id $APP_ID \
  --build-spec file://amplify.yml

# Create branch
aws amplify create-branch \
  --app-id $APP_ID \
  --branch-name main

# Set environment variables
aws amplify update-branch \
  --app-id $APP_ID \
  --branch-name main \
  --environment-variables \
    NEXT_PUBLIC_API_URL=https://your-api-url.com \
    POSTGRES_URL=postgresql://user:pass@host:5432/db
```

### Manual Console Setup

1. **Go to AWS Amplify Console**
2. **Click "New app" → "Host web app"**
3. **Select "GitHub" and authorize**
4. **Select repository and branch**
5. **Configure as monorepo** with `frontend` as app root
6. **Set environment variables**
7. **Deploy**

### Build Configuration

The build configuration in `amplify.yml`:

```yaml
version: 1
applications:
  - frontend:
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
    appRoot: frontend
```

### Environment Variables

Set these in AWS Amplify Console:
- `NEXT_PUBLIC_API_URL`: Your backend API URL
- `POSTGRES_URL`: Your database connection string
- `NEXT_PUBLIC_ENVIRONMENT`: Environment name (staging/production)

## Custom Domain Setup

### For Amplify

```bash
# Add custom domain
aws amplify create-domain-association \
  --app-id YOUR_APP_ID \
  --domain-name yourdomain.com \
  --sub-domain-settings prefix=app,branchName=main

# Get domain association status
aws amplify get-domain-association \
  --app-id YOUR_APP_ID \
  --domain-name yourdomain.com
```

### DNS Configuration

**DNS Records to Add:**
1. **CNAME Record**: `app` → `<branch>.<app-id>.amplifyapp.com`
2. **Verification Record**: `_<verification-id>.app` → `_<verification-value>.acm-validations.aws`

### Domain Status Progression
- `CREATING` → `REQUESTING_CERTIFICATE` → `PENDING_VERIFICATION` → `PENDING_DEPLOYMENT` → `AVAILABLE`

### Cloudflare Configuration

If using Cloudflare:
1. Log in to Cloudflare
2. Select your domain
3. Go to DNS settings
4. Add CNAME record for subdomain
5. Set Proxy status to "DNS only" (gray cloud)

## CI/CD Pipeline

### GitHub Secrets Required

Add these to your GitHub repository secrets:
- `AWS_ACCESS_KEY_ID` - AWS access key for deployment
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `CLOUDFRONT_DISTRIBUTION_ID` - CloudFront ID (after initial deployment)
- `AMPLIFY_APP_ID` - Your Amplify app ID
- `NEON_DATABASE_URL_STAGING` - Staging database connection string
- `NEON_DATABASE_URL_PROD` - Production database connection string

### GitHub Actions Workflows

**Backend CI/CD** (`.github/workflows/backend-ci.yml`):
- Runs tests and linting
- Builds Docker image
- Pushes to ECR
- Deploys to ECS

**Frontend CI/CD** (`.github/workflows/frontend-ci.yml`):
- Runs tests and builds
- Deploys to S3/CloudFront or triggers Amplify build

**Security Scanning** (`.github/workflows/security-scan.yml`):
- Runs security scans on dependencies
- Checks for vulnerabilities
- Generates security reports

## Docker Deployment

### Development

```bash
# Start all services
docker-compose up

# Start specific services
docker-compose up backend frontend
```

### Production

```bash
# Build production image
docker build -t oncall-agent -f backend/Dockerfile.prod backend/

# Run with environment file
docker run -p 8000:8000 --env-file backend/.env oncall-agent

# Run with explicit environment variables
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your-key \
  -e DATABASE_URL=your-db-url \
  oncall-agent
```

### Docker Compose Production

```yaml
version: '3.8'
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - K8S_ENABLED=true
    volumes:
      - ~/.kube/config:/root/.kube/config:ro

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - POSTGRES_URL=${POSTGRES_URL}
```

## Environment-Specific Deployments

### Staging Deployment

```bash
# Use staging environment variables
export NODE_ENV=staging
export DATABASE_URL=$NEON_DATABASE_URL_STAGING

# Deploy to staging
cd frontend
npm run build:staging
npm run deploy:staging
```

### Production Deployment

```bash
# Use production environment variables
export NODE_ENV=production
export DATABASE_URL=$NEON_DATABASE_URL_PROD

# Deploy to production (requires approval)
cd frontend
npm run build:production
npm run deploy:production
```

## Monitoring and Logging

### CloudWatch Integration

The deployment includes:
- **Application Logs**: ECS task logs sent to CloudWatch
- **Performance Metrics**: Custom metrics for response times and error rates
- **Alarms**: Automated alerting for critical issues
- **Dashboards**: Real-time monitoring dashboards

### Log Aggregation

```bash
# View application logs
aws logs tail /ecs/dreamops-backend --follow

# View specific log streams
aws logs describe-log-streams --log-group-name /ecs/dreamops-backend

# Search logs
aws logs filter-log-events \
  --log-group-name /ecs/dreamops-backend \
  --filter-pattern "ERROR"
```

## Scaling Configuration

### Auto Scaling

The ECS deployment includes auto-scaling based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Request count per target

### Manual Scaling

```bash
# Scale ECS service
aws ecs update-service \
  --cluster dreamops-cluster \
  --service dreamops-backend \
  --desired-count 3

# Scale database connections
# Update connection pool size in application configuration
```

## Security Configuration

### Secrets Management

- **API Keys**: Stored in AWS Secrets Manager
- **Database Credentials**: Rotated automatically
- **SSL Certificates**: Managed by AWS Certificate Manager
- **Network Security**: VPC with security groups

### Security Groups

- **ALB Security Group**: HTTP/HTTPS from internet
- **ECS Security Group**: HTTP from ALB only
- **Database Security Group**: PostgreSQL from ECS only

## Troubleshooting

### Common Deployment Issues

**Build Failures:**
1. Check environment variables are set correctly
2. Verify all dependencies are installed
3. Check build logs in AWS Console
4. Ensure sufficient build resources

**Connection Issues:**
1. Verify security group rules
2. Check DNS resolution
3. Validate SSL certificates
4. Test network connectivity

**Performance Issues:**
1. Check CloudWatch metrics
2. Analyze application logs
3. Monitor resource utilization
4. Optimize database queries

### Health Checks

```bash
# Test API health
curl https://your-api-url.com/health

# Test frontend
curl https://your-frontend-url.com

# Test database connection
cd frontend && npm run test:db
```

### Rollback Procedures

**ECS Rollback:**
```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster dreamops-cluster \
  --service dreamops-backend \
  --task-definition dreamops-backend:PREVIOUS_REVISION
```

**Frontend Rollback:**
```bash
# Amplify rollback
aws amplify start-job \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --job-type RELEASE \
  --job-id PREVIOUS_JOB_ID
```

## Cost Optimization

### Resource Right-Sizing

- **ECS Tasks**: Start with small instances and scale based on usage
- **Database**: Use appropriate instance sizes for each environment
- **Storage**: Implement lifecycle policies for logs and backups

### Reserved Instances

- Consider reserved instances for production workloads
- Use Savings Plans for flexible compute usage
- Monitor usage patterns for optimization opportunities

## Maintenance

### Regular Tasks

1. **Security Updates**: Keep base images and dependencies updated
2. **Certificate Renewal**: Monitor SSL certificate expiration
3. **Backup Verification**: Test database backup and restore procedures
4. **Performance Review**: Analyze metrics and optimize as needed

### Automated Maintenance

- **Dependency Updates**: Automated security patches
- **Log Rotation**: Automatic cleanup of old logs
- **Health Monitoring**: Automated restart of unhealthy services
- **Backup Scheduling**: Daily database backups 