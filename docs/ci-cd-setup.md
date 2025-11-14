# CI/CD Setup Guide

This document explains how to set up continuous deployment for DreamOps.

## Overview

DreamOps uses GitHub Actions for CI/CD with three workflows:

1. **deploy-backend.yml** - Deploys only backend changes
2. **deploy-frontend.yml** - Deploys only frontend changes
3. **deploy-all.yml** - Deploys both backend and frontend (triggered on any code change)

## Deployment Flow

```
Push to main branch
     ↓
GitHub Actions triggered
     ↓
Build Docker images
     ↓
Push to Amazon ECR
     ↓
SSH to production server (37.27.115.235)
     ↓
Pull new images
     ↓
Restart containers via docker compose
     ↓
Health check validation
     ↓
Cleanup old images
```

## Required GitHub Secrets

Add these secrets to your GitHub repository settings (Settings → Secrets and variables → Actions → New repository secret):

### AWS Credentials
- **AWS_ACCESS_KEY_ID**
  - Description: AWS access key for ECR access
  - How to get: Create an IAM user with `AmazonEC2ContainerRegistryPowerUser` policy
  - Example: `AKIAIOSFODNN7EXAMPLE`

- **AWS_SECRET_ACCESS_KEY**
  - Description: AWS secret key for ECR access
  - How to get: Same IAM user as above
  - Example: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

### Production Server Access
- **PRODUCTION_SERVER_HOST**
  - Description: IP address of production server
  - Value: `37.27.115.235`

- **PRODUCTION_SERVER_USER**
  - Description: SSH username for production server
  - Value: `root`

- **PRODUCTION_SERVER_SSH_KEY**
  - Description: Private SSH key for authentication
  - How to get: Run this on your local machine that has SSH access:
    ```bash
    cat ~/.ssh/id_rsa
    ```
  - Paste the entire key including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`

### Database Configuration
- **POSTGRES_URL**
  - Description: PostgreSQL connection string for Neon database (production)
  - Format: `postgresql://user:password@host/database?sslmode=require`
  - Example: `postgresql://neondb_owner:npg_XXX@ep-xxx.neon.tech/neondb?sslmode=require`
  - Note: This is used during frontend build time for database migrations

## Setting Up AWS IAM User for CI/CD

1. Go to AWS IAM Console
2. Click "Users" → "Create user"
3. User name: `dreamops-github-actions`
4. Click "Next"
5. Select "Attach policies directly"
6. Add these policies:
   - `AmazonEC2ContainerRegistryPowerUser` (for ECR push/pull)
7. Click "Create user"
8. Click on the created user
9. Go to "Security credentials" tab
10. Click "Create access key"
11. Select "Application running outside AWS"
12. Copy the Access Key ID and Secret Access Key
13. Add them to GitHub secrets

## Setting Up SSH Access

The production server needs AWS CLI configured to pull images from ECR:

```bash
# SSH into production server
ssh root@37.27.115.235

# Install AWS CLI if not already installed
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI with the same IAM credentials
aws configure
# Enter:
# - AWS Access Key ID: [from IAM user]
# - AWS Secret Access Key: [from IAM user]
# - Default region: us-east-1
# - Default output format: json
```

## Workflow Triggers

### deploy-backend.yml
Triggers on:
- Push to `main` branch when `backend/**` files change
- Manual trigger via GitHub Actions UI

### deploy-frontend.yml
Triggers on:
- Push to `main` branch when `frontend/**` files change
- Manual trigger via GitHub Actions UI

### deploy-all.yml
Triggers on:
- Push to `main` branch (any code changes except docs)
- Manual trigger via GitHub Actions UI

## Deployment Safety Features

1. **Health Checks**:
   - Backend: Checks `http://127.0.0.1:8000/health`
   - Frontend: Checks `http://127.0.0.1:3000`
   - 60-second timeout with automatic rollback on failure

2. **Automatic Rollback**:
   - If health checks fail, deployment exits with error
   - Docker Compose maintains previous containers
   - Logs are displayed for debugging

3. **Image Cleanup**:
   - Removes Docker images older than 72 hours
   - Prevents disk space issues
   - Only runs if deployment succeeds

4. **Deployment Validation**:
   - Waits for containers to be fully started
   - Validates HTTP responses before marking as successful
   - Shows container status at the end

## Manual Deployment

You can manually trigger deployments:

1. Go to GitHub repository → Actions
2. Select the workflow you want to run
3. Click "Run workflow"
4. Select branch (usually `main`)
5. Click "Run workflow"

## Troubleshooting

### Deployment fails with "Backend failed to start"
```bash
# SSH into server
ssh root@37.27.115.235

# Check backend logs
cd /opt/dreamops
docker compose logs backend --tail=100

# Check if backend is running
docker compose ps

# Manually restart if needed
docker compose restart backend
```

### Deployment fails with "Frontend failed to start"
```bash
# SSH into server
ssh root@37.27.115.235

# Check frontend logs
cd /opt/dreamops
docker compose logs frontend --tail=100

# Check if frontend is running
docker compose ps

# Manually restart if needed
docker compose restart frontend
```

### ECR authentication fails
```bash
# SSH into server
ssh root@37.27.115.235

# Re-configure AWS CLI
aws configure

# Test ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### SSH connection fails
- Verify `PRODUCTION_SERVER_SSH_KEY` secret is correct
- Verify `PRODUCTION_SERVER_HOST` is `37.27.115.235`
- Verify `PRODUCTION_SERVER_USER` is `root`
- Test SSH manually: `ssh root@37.27.115.235`

## Monitoring Deployments

### View deployment status
1. Go to GitHub repository → Actions
2. Click on the running workflow
3. Monitor real-time logs

### Check running services
```bash
ssh root@37.27.115.235 "cd /opt/dreamops && docker compose ps"
```

### View service logs
```bash
# Backend logs
ssh root@37.27.115.235 "cd /opt/dreamops && docker compose logs backend --tail=50"

# Frontend logs
ssh root@37.27.115.235 "cd /opt/dreamops && docker compose logs frontend --tail=50"

# All logs
ssh root@37.27.115.235 "cd /opt/dreamops && docker compose logs --tail=50"
```

## Deployment Best Practices

1. **Test locally first**: Always test changes in a local Docker environment before pushing
2. **Review logs**: Check GitHub Actions logs for any warnings
3. **Monitor health**: Verify services are healthy after deployment
4. **Gradual rollout**: Deploy backend first, then frontend if they're coupled
5. **Keep secrets updated**: Rotate AWS credentials periodically

## Security Considerations

1. **SSH Key**: Use a dedicated SSH key for CI/CD, not your personal key
2. **AWS Credentials**: Use IAM user with minimal required permissions
3. **Secrets Rotation**: Rotate all secrets every 90 days
4. **Access Logs**: Monitor AWS CloudTrail for ECR access
5. **Server Access**: Limit SSH access to GitHub Actions IPs if possible

## Disaster Recovery

If deployment completely fails:

```bash
# SSH into server
ssh root@37.27.115.235
cd /opt/dreamops

# Stop all containers
docker compose down

# Pull specific working version (replace SHA with working commit)
docker pull YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dreamops-backend:WORKING_SHA
docker pull YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dreamops-frontend:WORKING_SHA

# Tag as latest
docker tag YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dreamops-backend:WORKING_SHA \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dreamops-backend:latest

docker tag YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dreamops-frontend:WORKING_SHA \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dreamops-frontend:latest

# Start containers
docker compose up -d

# Verify
docker compose ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:3000
```

## Next Steps

After setting up CI/CD:

1. ✅ Add all required GitHub secrets
2. ✅ Configure AWS CLI on production server
3. ✅ Test deployment with a small change
4. ✅ Set up monitoring for failed deployments
5. ✅ Configure Authentik for oncall.frai.pro
6. ✅ Document any environment-specific configuration
