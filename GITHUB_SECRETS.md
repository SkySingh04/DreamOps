# GitHub Secrets Configuration Guide

This guide lists all the GitHub Secrets required for the CI/CD pipelines to work correctly.

## Required GitHub Secrets

Navigate to your repository → Settings → Secrets and variables → Actions, then add:

### 1. AWS Credentials (Required for Deployment)
- **`AWS_ACCESS_KEY_ID`**
  - Description: AWS access key for deployment operations
  - Required permissions: ECS, ECR, S3, CloudFront, IAM, CloudWatch
  - Example: `AKIAIOSFODNN7EXAMPLE`

- **`AWS_SECRET_ACCESS_KEY`**
  - Description: AWS secret access key
  - Example: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

### 2. API Keys (Required for Runtime)
- **`ANTHROPIC_API_KEY`**
  - Description: Your Anthropic API key for Claude AI
  - Get from: https://console.anthropic.com/account/keys
  - Example: `sk-ant-api03-...`

### 3. Infrastructure References (Add After Initial Deployment)
- **`CLOUDFRONT_DISTRIBUTION_ID`**
  - Description: CloudFront distribution ID for frontend
  - Get from: Terraform output after first deployment
  - Example: `E1QXVPK7EXAMPLE`

- **`REACT_APP_API_URL`**
  - Description: Backend API URL for frontend to connect to
  - Get from: Terraform output (ALB DNS name)
  - Example: `http://oncall-agent-backend-alb-123456.us-east-1.elb.amazonaws.com`

### 4. Optional Secrets
- **`GITHUB_TOKEN`** (if using GitHub MCP integration)
  - Description: GitHub personal access token
  - Permissions needed: repo, workflow, issues
  - Note: GitHub automatically provides a token, but you may need a PAT for cross-repo access

## Step-by-Step Setup

### Before First Deployment

1. Create AWS IAM user for CI/CD with necessary permissions
2. Generate access keys for the IAM user
3. Add these secrets to GitHub:
   ```
   AWS_ACCESS_KEY_ID=<your-access-key>
   AWS_SECRET_ACCESS_KEY=<your-secret-key>
   ANTHROPIC_API_KEY=<your-anthropic-key>
   ```

### After First Deployment

1. Run Terraform to create infrastructure:
   ```bash
   cd infrastructure/terraform
   terraform init
   terraform apply
   ```

2. Note the outputs:
   ```
   backend_api_url = "http://oncall-agent-backend-alb-xxxxx.elb.amazonaws.com"
   cloudfront_distribution_id = "E1QXVPK7EXAMPLE"
   ```

3. Add these to GitHub Secrets:
   ```
   REACT_APP_API_URL=<backend_api_url from terraform>
   CLOUDFRONT_DISTRIBUTION_ID=<cloudfront_distribution_id from terraform>
   ```

## Verifying Secrets

To verify your secrets are configured correctly:

1. Go to Actions tab in your repository
2. Manually trigger a workflow run
3. Check the logs for any authentication errors

## Security Best Practices

1. **Rotate Keys Regularly**: Change AWS access keys every 90 days
2. **Use Least Privilege**: Create an IAM user specifically for CI/CD with minimal permissions
3. **Enable MFA**: On your AWS root account and IAM users
4. **Audit Access**: Regularly review who has access to these secrets
5. **Use AWS IAM Roles**: For production, consider using OIDC with GitHub Actions instead of long-lived credentials

## Troubleshooting

### "Invalid AWS credentials" error
- Verify the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are correct
- Check if the IAM user has necessary permissions
- Ensure the keys haven't been rotated

### "ANTHROPIC_API_KEY is not set" error
- Verify the secret name is exactly `ANTHROPIC_API_KEY`
- Check if the key is still valid in Anthropic console

### "CloudFront distribution not found" error
- Ensure you've run Terraform first to create infrastructure
- Verify the CLOUDFRONT_DISTRIBUTION_ID matches terraform output

## CI/CD Workflow Files

These secrets are used by:
- `.github/workflows/backend-ci.yml` - Backend testing and deployment
- `.github/workflows/frontend-ci.yml` - Frontend testing and deployment
- `.github/workflows/security-scan.yml` - Security scanning

## Need Help?

If you encounter issues:
1. Check the GitHub Actions logs for specific error messages
2. Verify all required secrets are set
3. Ensure your AWS IAM user has the necessary permissions
4. Create an issue in the repository with error details