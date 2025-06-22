# Quick AWS Amplify Deployment

## Option 1: AWS CLI Commands (Recommended)

Run these commands to create and deploy your Amplify app:

```bash
# 1. Create Amplify App
aws amplify create-app \
  --name "dreamops-frontend" \
  --repository "https://github.com/SkySingh04/DreamOps" \
  --platform "WEB_COMPUTE" \
  --region ap-south-1

# Note the App ID from the output (looks like: d1234abcd)

# 2. Create build specification
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

# 3. Update app with build spec
aws amplify update-app \
  --app-id YOUR_APP_ID \
  --build-spec file://amplify.yml \
  --region ap-south-1

# 4. Create branch
aws amplify create-branch \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --region ap-south-1

# 5. Set environment variables
aws amplify update-branch \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --environment-variables \
    NEXT_PUBLIC_API_URL=https://your-api-url.com \
    POSTGRES_URL=postgresql://user:pass@host:5432/db \
  --region ap-south-1
```

## Option 2: AWS Console (Easiest)

1. **Go to AWS Amplify Console**
   - https://ap-south-1.console.aws.amazon.com/amplify/

2. **Click "New app" → "Host web app"**

3. **Select "GitHub" and authorize**

4. **Select repository**
   - Repository: `SkySingh04/DreamOps`
   - Branch: `main`

5. **Configure build settings**
   - App name: `dreamops-frontend`
   - Check "My app is a monorepo"
   - App root directory: `frontend`

6. **Update build settings** (click Edit YML):
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

7. **Add environment variables**:
   - `NEXT_PUBLIC_API_URL`: Your backend API URL
   - `POSTGRES_URL`: Your database connection string

8. **Click "Save and deploy"**

## After Deployment

Your app will be available at:
```
https://main.YOUR_APP_ID.amplifyapp.com
```

To get the URL via CLI:
```bash
aws amplify get-app \
  --app-id YOUR_APP_ID \
  --region ap-south-1 \
  --query 'app.defaultDomain' \
  --output text
```

## Custom Domain (Optional)

```bash
# Add custom domain
aws amplify create-domain-association \
  --app-id YOUR_APP_ID \
  --domain-name yourdomain.com \
  --region ap-south-1

# Add subdomain
aws amplify create-subdomain \
  --app-id YOUR_APP_ID \
  --domain-name yourdomain.com \
  --subdomain-setting prefix=www,branchName=main \
  --region ap-south-1
```

## Troubleshooting

1. **Build fails**: Check the build logs in Amplify Console
2. **Environment variables**: Ensure all required env vars are set
3. **Monorepo issues**: Make sure `appRoot: frontend` is set correctly
4. **Database connection**: Use placeholder URL if you don't have a database yet