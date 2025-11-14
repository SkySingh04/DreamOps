# Quick Start: CI/CD Setup

## GitHub Secrets to Add

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add these **5 secrets**:

### 1. AWS_ACCESS_KEY_ID
```
Your AWS IAM access key for ECR
```

### 2. AWS_SECRET_ACCESS_KEY
```
Your AWS IAM secret key for ECR
```

### 3. PRODUCTION_SERVER_HOST
```
37.27.115.235
```

### 4. PRODUCTION_SERVER_USER
```
root
```

### 5. PRODUCTION_SERVER_SSH_KEY
```
Run this on your machine: cat ~/.ssh/id_rsa
Paste the ENTIRE output including headers
```

### 6. POSTGRES_URL
```
Your Neon database production connection string
Format: postgresql://user:password@host/database?sslmode=require
```

---

## Authentik Configuration (OAuth2 Setup - 2 Steps)

### 1. Login to Authentik
https://authentik.frai.pro/if/admin/

### 2. Create OAuth2 Provider
- Navigate: **Applications** → **Providers** → **Create**
- Type: **OAuth2/OpenID Provider**
- Name: `oncall`
- Authorization flow: `default-provider-authorization-implicit-consent`
- **Redirect URIs**: `https://oncall.frai.pro/oauth2/callback`
- Click **Finish**

### 3. Create Application
- Navigate: **Applications** → **Applications** → **Create**
- Name: `DreamOps Oncall` (or just `oncall`)
- Slug: `oncall` ⚠️ **Important: must be exactly "oncall"**
- Provider: Select `oncall` (the provider you just created)
- Click **Create**

### 4. Verify Deployment
Once you've created the provider and application, the oauth2-proxy pod will automatically restart and connect to Authentik.

Check status:
```bash
kubectl get pods -n default -l k8s-app=oauth2-proxy-dreamops
```

The oauth2-proxy handles all authentication - you don't need to configure anything else!

---

## Testing CI/CD

### Option 1: Push a small change
```bash
git add .
git commit -m "test: trigger ci/cd"
git push origin main
```

### Option 2: Manual trigger
1. Go to GitHub → Actions
2. Select "Deploy All Services"
3. Click "Run workflow"
4. Click "Run workflow" button

---

## Verify Deployment

```bash
# Check if services are running
ssh root@37.27.115.235 "cd /opt/dreamops && docker compose ps"

# Check backend health
curl https://oncall.frai.pro/health

# Access the app
open https://oncall.frai.pro
```

---

## Deployment happens automatically when you:
- ✅ Push to `main` branch
- ✅ Merge a PR to `main`
- ✅ Manually trigger via GitHub Actions

## Deployment flow:
1. Build Docker images
2. Push to AWS ECR
3. SSH to production server
4. Pull new images
5. Restart containers
6. Health check validation
7. Rollback if failed

Full documentation: `docs/ci-cd-setup.md`
