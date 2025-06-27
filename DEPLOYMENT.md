# DreamOps Render Deployment Guide

This guide covers deploying DreamOps on Render with separate staging and production environments.

## Prerequisites

1. **GitHub Repository**: Ensure your code is pushed to GitHub
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **Neon Databases**: You should have already set up:
   - Staging database (from `backend/.env.staging`)
   - Production database (from `backend/.env.production`)

## Branch Strategy

- `staging` branch → Staging environment
- `main` branch → Production environment

## Step-by-Step Deployment

### 1. Push Branches to GitHub

```bash
# Create and push staging branch
git checkout -b staging
git push -u origin staging

# Ensure main branch is pushed
git checkout main
git push -u origin main
```

### 2. Deploy Staging Environment

#### Deploy Backend (Staging)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `dreamops-backend-staging`
   - **Environment**: Python
   - **Branch**: `staging`
   - **Root Directory**: Leave blank (uses repository root)
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python api_server.py`

5. Set environment variables:
   ```
   # Required (must add values in Render):
   ANTHROPIC_API_KEY=<your-anthropic-api-key>
   DATABASE_URL=<staging-database-url-from-env-staging>
   PAGERDUTY_WEBHOOK_SECRET=<your-pagerduty-webhook-secret>
   PAGERDUTY_API_KEY=<your-pagerduty-api-key>
   PAGERDUTY_USER_EMAIL=<your-pagerduty-email>
   
   # Auto-configured:
   CORS_ORIGINS=https://<your-frontend-staging-url>.onrender.com
   ```

6. Click "Create Web Service"

#### Deploy Frontend (Staging)

1. Click "New +" → "Web Service"
2. Connect the same GitHub repository
3. Configure the service:
   - **Name**: `dreamops-frontend-staging`
   - **Environment**: Node
   - **Branch**: `staging`
   - **Root Directory**: Leave blank
   - **Build Command**: `cd frontend && npm install && npm run build:staging`
   - **Start Command**: `cd frontend && npm run start`

4. Set environment variables:
   ```
   # Required (must add values in Render):
   POSTGRES_URL=<staging-database-url>
   NEXT_PUBLIC_DATABASE_URL=<staging-database-url>
   AUTH_SECRET=<generate-random-secret>
   
   # Update after backend is deployed:
   NEXT_PUBLIC_API_URL=https://<your-backend-staging-url>.onrender.com
   NEXT_PUBLIC_WS_URL=https://<your-backend-staging-url>.onrender.com
   ```

5. Click "Create Web Service"

### 3. Deploy Production Environment

Repeat the above steps but with these changes:

#### Backend (Production)
- **Name**: `dreamops-backend-prod`
- **Branch**: `main`
- **Build Command**: `cd backend && pip install -r requirements.txt`
- **Start Command**: `cd backend && python api_server.py`
- **Environment Variables**: Use production database URL and update CORS_ORIGINS

#### Frontend (Production)
- **Name**: `dreamops-frontend-prod`
- **Branch**: `main`
- **Build Command**: `cd frontend && npm install && npm run build:production`
- **Start Command**: `cd frontend && npm run start`
- **Environment Variables**: Use production database URL and API URLs

### 4. Update CORS Origins

After both services are deployed, update the backend CORS_ORIGINS:

**Staging Backend**:
```
CORS_ORIGINS=https://dreamops-frontend-staging-xxx.onrender.com
```

**Production Backend**:
```
CORS_ORIGINS=https://dreamops-frontend-prod-xxx.onrender.com,https://yourdomain.com
```

## Environment Variables Reference

### Backend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| ANTHROPIC_API_KEY | Your Anthropic API key | sk-ant-api03-xxx |
| DATABASE_URL | PostgreSQL connection string | postgresql://user:pass@host/db |
| CORS_ORIGINS | Allowed frontend URLs (comma-separated) | https://frontend.onrender.com |
| PAGERDUTY_WEBHOOK_SECRET | PagerDuty webhook secret | your-webhook-secret |
| PAGERDUTY_API_KEY | PagerDuty API key | your-api-key |
| PAGERDUTY_USER_EMAIL | PagerDuty user email | user@company.com |

### Frontend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| POSTGRES_URL | PostgreSQL connection string | postgresql://user:pass@host/db |
| NEXT_PUBLIC_DATABASE_URL | Same as POSTGRES_URL | postgresql://user:pass@host/db |
| NEXT_PUBLIC_API_URL | Backend API URL | https://backend.onrender.com |
| AUTH_SECRET | Random secret for auth | generate-random-string |
| NODE_ENV | Environment name | staging or production |

## Post-Deployment Verification

### 1. Health Checks

**Backend Health**:
```bash
curl https://your-backend-url.onrender.com/health
```

**Frontend Health**:
```bash
curl https://your-frontend-url.onrender.com
```

### 2. Database Migrations

Run migrations for each environment:

```bash
# Local machine - staging
cd frontend
cp .env.staging .env
npm run db:migrate:staging

# Local machine - production
cp .env.production .env
npm run db:migrate:production
```

### 3. Test API Integration

1. Open frontend URL in browser
2. Check browser console for any API errors
3. Try logging in or creating an incident

### 4. Configure PagerDuty Webhook

In PagerDuty:
1. Go to Integrations → Generic Webhooks
2. Add webhook URL: `https://your-backend-url.onrender.com/webhook/pagerduty`
3. Test the webhook

## Monitoring and Logs

### View Logs
- Go to Render Dashboard
- Click on your service
- Navigate to "Logs" tab

### Common Log Commands
```bash
# Check for startup errors
# Look for: "Uvicorn running on http://0.0.0.0:10000"

# Check API requests
# Look for: "POST /webhook/pagerduty"

# Check CORS issues
# Look for: "CORS" in error messages
```

## Troubleshooting

### Backend Issues

**Port Binding Error**:
- Ensure using `PORT` environment variable
- Check start command uses `0.0.0.0` as host

**CORS Errors**:
- Verify CORS_ORIGINS includes your frontend URL
- Restart backend after updating environment variables

**Database Connection Failed**:
- Verify DATABASE_URL is correct
- Ensure `?sslmode=require` is in the connection string
- Check Neon database is not suspended

### Frontend Issues

**API Connection Failed**:
- Verify NEXT_PUBLIC_API_URL points to backend
- Check backend is running and healthy
- Look for CORS errors in browser console

**Build Failures**:
- Check Node version compatibility
- Ensure all dependencies are in package.json
- Review build logs for specific errors

**Database Errors**:
- Verify POSTGRES_URL matches your Neon database
- Run migrations: `npm run db:migrate:staging`

### Common Fixes

1. **Restart Service**: 
   - Go to service in Render Dashboard
   - Click "Manual Deploy" → "Deploy"

2. **Clear Build Cache**:
   - Go to Settings → "Clear build cache"
   - Trigger new deploy

3. **Environment Variable Changes**:
   - After updating env vars, restart the service
   - Some variables require rebuild (use Manual Deploy)

## Security Checklist

- [ ] All sensitive environment variables use `sync: false`
- [ ] AUTH_SECRET is unique per environment
- [ ] Database URLs are environment-specific
- [ ] CORS_ORIGINS only includes your domains
- [ ] API keys are kept secret and rotated regularly

## Deployment Automation

To deploy using render.yaml files:

1. **Staging**: 
   ```bash
   render blueprint launch --file render-staging.yaml
   ```

2. **Production**:
   ```bash
   render blueprint launch --file render-prod.yaml
   ```

Note: You'll still need to add sensitive environment variables through the Render dashboard.

## Rollback Procedure

If issues occur after deployment:

1. Go to service in Render Dashboard
2. Click "Events" tab
3. Find previous successful deploy
4. Click "Rollback to this deploy"

## Support

For Render-specific issues:
- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com)

For DreamOps issues:
- Check logs in Render Dashboard
- Review this deployment guide
- Ensure all environment variables are set correctly