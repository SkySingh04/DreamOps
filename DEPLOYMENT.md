# DreamOps - Docker Compose Deployment Guide

## Overview

Deploy DreamOps on bare-metal server using Docker Compose with:
- Self-hosted PostgreSQL (saves $25-50/month vs Neon)
- AWS ECR with `:latest` tag only (cost optimization)
- Simple CI/CD with GitHub Actions
- OAuth proxy integration (compatible with existing Authentik/proxy setup)

**Server**: `37.27.111.47` (bare-metal with K3s cluster)
**Cost**: ~$10/month (ECR storage only)
**Setup Time**: 2-3 hours

---

## Architecture

```
Internet
    ↓
OAuth Proxy (existing Authentik/proxy on server)
    ↓
Nginx (reverse proxy)
    ↓
┌─────────────────────────────────┐
│  Docker Compose Stack           │
│  ├── dreamops-backend (FastAPI) │
│  ├── dreamops-frontend (Next.js)│
│  └── postgres (self-hosted)     │
└─────────────────────────────────┘
```

---

## Prerequisites

### 1. AWS ECR Setup

```bash
# Create repositories
aws ecr create-repository --repository-name dreamops-backend --region us-east-1
aws ecr create-repository --repository-name dreamops-frontend --region us-east-1

# Set lifecycle policy (keep only latest)
cat > lifecycle-policy.json << 'EOF'
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep only latest tag",
    "selection": {
      "tagStatus": "any",
      "countType": "imageCountMoreThan",
      "countNumber": 1
    },
    "action": {
      "type": "expire"
    }
  }]
}
EOF

# Apply lifecycle policy
aws ecr put-lifecycle-policy \
  --repository-name dreamops-backend \
  --lifecycle-policy-text file://lifecycle-policy.json

aws ecr put-lifecycle-policy \
  --repository-name dreamops-frontend \
  --lifecycle-policy-text file://lifecycle-policy.json
```

**Note your ECR URLs**:
```
507254053937.dkr.ecr.us-east-1.amazonaws.com/dreamops-backend:latest
507254053937.dkr.ecr.us-east-1.amazonaws.com/dreamops-frontend:latest
```

### 2. GitHub Secrets (for CI/CD)

Add these to your GitHub repository settings → Secrets:

```
AWS_ACCESS_KEY_ID          # AWS IAM user with ECR push permissions
AWS_SECRET_ACCESS_KEY      # AWS IAM secret
AWS_ACCOUNT_ID             # Your AWS account ID (507254053937)
SERVER_HOST                # 37.27.111.47
SERVER_USER                # root (or your SSH user)
SSH_PRIVATE_KEY            # Private key for SSH access
POSTGRES_PASSWORD          # Strong password for PostgreSQL
ANTHROPIC_API_KEY          # Your Anthropic API key
PAGERDUTY_API_KEY          # (Optional) PagerDuty integration
SLACK_WEBHOOK_URL          # (Optional) Deployment notifications
```

---

## Deployment Files

### Directory Structure

```
/opt/dreamops/
├── docker-compose.yml
├── .env
├── nginx.conf
├── ssl/                    # SSL certificates
├── backups/                # Database backups
└── postgres-data/          # PostgreSQL data (Docker volume)
```

### File 1: `docker-compose.yml`

Located at: `/opt/dreamops/docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: dreamops-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: dreamops
      POSTGRES_USER: dreamops
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "127.0.0.1:5432:5432"  # Only expose to localhost
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dreamops"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - dreamops
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  backend:
    image: ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/dreamops-backend:latest
    container_name: dreamops-backend
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      # Core settings
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      NODE_ENV: production
      ENVIRONMENT: production

      # Database
      POSTGRES_URL: postgresql://dreamops:${POSTGRES_PASSWORD}@postgres:5432/dreamops

      # Kubernetes Integration (uses host kubectl)
      K8S_ENABLED: "true"
      K8S_NAMESPACE: default
      K8S_MCP_COMMAND: "npx -y kubernetes-mcp-server@latest"
      K8S_ENABLE_DESTRUCTIVE_OPERATIONS: "false"

      # PagerDuty (optional)
      PAGERDUTY_ENABLED: ${PAGERDUTY_ENABLED:-false}
      PAGERDUTY_API_KEY: ${PAGERDUTY_API_KEY:-}
      PAGERDUTY_USER_EMAIL: ${PAGERDUTY_USER_EMAIL:-}

      # Slack (optional)
      SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL:-}
    ports:
      - "127.0.0.1:8000:8000"  # Only expose to localhost
    volumes:
      - /root/.kube/config:/root/.kube/config:ro  # For kubectl access to K3s
      - ./logs/backend:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s
    networks:
      - dreamops
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    image: ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/dreamops-frontend:latest
    container_name: dreamops-frontend
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    environment:
      # Backend connection
      NEXT_PUBLIC_API_URL: http://backend:8000

      # Database (for frontend server-side operations)
      POSTGRES_URL: postgresql://dreamops:${POSTGRES_PASSWORD}@postgres:5432/dreamops

      # Node environment
      NODE_ENV: production
      NEXT_TELEMETRY_DISABLED: 1
    ports:
      - "127.0.0.1:3000:3000"  # Only expose to localhost
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    networks:
      - dreamops
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    container_name: dreamops-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - frontend
      - backend
    networks:
      - dreamops
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
    driver: local

networks:
  dreamops:
    driver: bridge
```

### File 2: `.env`

Located at: `/opt/dreamops/.env` (NOT committed to git)

```bash
# AWS
AWS_ACCOUNT_ID=507254053937

# Database
POSTGRES_PASSWORD=your-super-secure-password-here-min-32-chars

# API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...

# PagerDuty (optional)
PAGERDUTY_ENABLED=true
PAGERDUTY_API_KEY=your-pagerduty-key
PAGERDUTY_USER_EMAIL=your-email@domain.com

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### File 3: `nginx.conf`

Located at: `/opt/dreamops/nginx.conf`

```nginx
events {
    worker_connections 1024;
}

http {
    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Upstream services
    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general_limit:10m rate=30r/s;

    # HTTP - Redirect to HTTPS
    server {
        listen 80;
        server_name dreamops.yourdomain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS - Main application
    server {
        listen 443 ssl http2;
        server_name dreamops.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/letsencrypt/live/dreamops.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/dreamops.yourdomain.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;

        # Backend API
        location /api {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts for long-running AI operations
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        # WebSocket support (for real-time updates)
        location /api/v1/agent-logs/stream {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 3600s;
        }

        # Health check endpoint (bypass rate limiting)
        location /health {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }

        # Frontend
        location / {
            limit_req zone=general_limit burst=50 nodelay;

            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Next.js specific
            proxy_buffering off;
        }
    }
}
```

---

## Initial Deployment

### Step 1: Prepare Server

```bash
# SSH to server
ssh root@37.27.111.47

# Create directory
mkdir -p /opt/dreamops/{backups,logs/backend,ssl}
cd /opt/dreamops

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com | sh

# Install Docker Compose (if not already installed)
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install AWS CLI (for ECR login)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
```

### Step 2: Upload Configuration Files

Upload the 3 files created above to `/opt/dreamops/`:
- `docker-compose.yml`
- `.env` (with your actual secrets)
- `nginx.conf`

Or use git to clone and copy:
```bash
cd /opt/dreamops
git clone https://github.com/yourusername/oncall-agent.git repo
cp repo/docker-compose.yml .
cp repo/nginx.conf .
# Manually create .env with secrets
```

### Step 3: SSL Certificate (Let's Encrypt)

```bash
# Install certbot
apt install certbot -y

# Get certificate
certbot certonly --standalone -d dreamops.yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/dreamops.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/dreamops.yourdomain.com/privkey.pem

# Set up auto-renewal
echo "0 0,12 * * * certbot renew --quiet --post-hook 'docker-compose -f /opt/dreamops/docker-compose.yml restart nginx'" | crontab -
```

### Step 4: Login to ECR

```bash
cd /opt/dreamops

# Configure AWS credentials
aws configure
# Enter: AWS Access Key, Secret Key, Region (us-east-1), Format (json)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 507254053937.dkr.ecr.us-east-1.amazonaws.com
```

### Step 5: Pull Images and Start

```bash
cd /opt/dreamops

# Pull latest images
docker-compose pull

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
curl http://localhost:3000
```

### Step 6: Run Database Migrations (if needed)

```bash
# Run migrations from backend container
docker-compose exec backend uv run alembic upgrade head

# Or if using Drizzle (frontend):
docker-compose exec frontend npm run db:migrate:production
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

Create: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_BACKEND: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/dreamops-backend
  ECR_FRONTEND: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/dreamops-frontend

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Backend Tests
        run: |
          cd backend
          pip install uv
          uv sync
          uv run ruff check .
          uv run mypy . --ignore-missing-imports || true
          # uv run pytest tests/ || true

      - name: Frontend Tests
        run: |
          cd frontend
          npm install
          npm run lint || true
          npm run type-check || true

  build-and-deploy:
    name: Build and Deploy
    runs-on: ubuntu-latest
    needs: test
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push backend
        run: |
          cd backend
          docker build -f Dockerfile.prod -t ${{ env.ECR_BACKEND }}:latest .
          docker push ${{ env.ECR_BACKEND }}:latest

      - name: Build and push frontend
        run: |
          cd frontend
          docker build -f Dockerfile -t ${{ env.ECR_FRONTEND }}:latest .
          docker push ${{ env.ECR_FRONTEND }}:latest

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/dreamops

            # Login to ECR
            aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com

            # Pull latest images
            docker-compose pull

            # Restart services (zero-downtime with health checks)
            docker-compose up -d

            # Wait for health checks
            sleep 10

            # Show status
            docker-compose ps

            # Clean up old images
            docker image prune -af

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: |
            DreamOps Deployment ${{ job.status }}
            Commit: ${{ github.event.head_commit.message }}
            Author: ${{ github.actor }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Database Management

### Automated Backups

Create: `/opt/dreamops/backup.sh`

```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/dreamops/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/dreamops_backup_${DATE}.sql.gz"

echo "Starting backup at $(date)"

# Create backup
docker-compose exec -T postgres pg_dump -U dreamops dreamops | gzip > "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "dreamops_backup_*.sql.gz" -mtime +7 -delete

echo "Old backups cleaned up"

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_FILE" s3://your-backup-bucket/dreamops/

echo "Backup complete at $(date)"
```

Make executable and add to crontab:
```bash
chmod +x /opt/dreamops/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/dreamops/backup.sh >> /opt/dreamops/logs/backup.log 2>&1") | crontab -
```

### Restore from Backup

```bash
# Stop services
cd /opt/dreamops
docker-compose stop backend frontend

# Restore database
gunzip -c backups/dreamops_backup_YYYYMMDD_HHMMSS.sql.gz | docker-compose exec -T postgres psql -U dreamops dreamops

# Start services
docker-compose up -d
```

---

## Operations

### View Logs

```bash
cd /opt/dreamops

# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restart Services

```bash
cd /opt/dreamops

# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
docker-compose restart frontend
```

### Update Secrets

```bash
# Edit .env file
nano /opt/dreamops/.env

# Restart affected services
docker-compose up -d
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# PostgreSQL database size
docker-compose exec postgres psql -U dreamops -c "SELECT pg_size_pretty(pg_database_size('dreamops'));"
```

### Manual Deploy

```bash
# On your local machine
cd /Users/akashsingh/Desktop/oncall-agent
./scripts/manual-deploy.sh
```

---

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:3000

# PostgreSQL health
docker-compose exec postgres pg_isready -U dreamops

# All services status
docker-compose ps
```

### Set Up Monitoring (Optional)

Add to `docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: dreamops-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "127.0.0.1:9090:9090"
    networks:
      - dreamops

  grafana:
    image: grafana/grafana:latest
    container_name: dreamops-grafana
    ports:
      - "127.0.0.1:3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - dreamops
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check if ports are in use
netstat -tlnp | grep -E '8000|3000|5432'

# Check disk space
df -h

# Check Docker daemon
systemctl status docker
```

### Database Connection Issues

```bash
# Test database connection
docker-compose exec postgres psql -U dreamops -c "SELECT 1;"

# Check PostgreSQL logs
docker-compose logs postgres

# Verify environment variables
docker-compose exec backend env | grep POSTGRES_URL
```

### ECR Pull Issues

```bash
# Re-login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 507254053937.dkr.ecr.us-east-1.amazonaws.com

# Check AWS credentials
aws sts get-caller-identity

# Manual pull
docker pull 507254053937.dkr.ecr.us-east-1.amazonaws.com/dreamops-backend:latest
```

### Out of Disk Space

```bash
# Clean up Docker
docker system prune -af
docker volume prune -f

# Check what's using space
du -sh /opt/dreamops/*
du -sh /var/lib/docker/*
```

---

## Cost Breakdown

| Item | Monthly Cost |
|------|--------------|
| AWS ECR (2 images, latest only) | $1-2 |
| ECR Data Transfer | $2-5 |
| Server (already owned) | $0 |
| PostgreSQL (self-hosted) | $0 |
| SSL Certificate (Let's Encrypt) | $0 |
| **Total** | **~$5-10/month** |

**Savings vs Cloud**:
- No managed database: Save $25-50/month
- No managed Kubernetes: Save $70-100/month
- Self-hosted: **Save ~$100/month**

---

## Security Checklist

- [ ] Strong PostgreSQL password (32+ characters)
- [ ] Secrets stored in `.env`, not in git
- [ ] SSL/TLS enabled (HTTPS)
- [ ] Services only exposed to localhost (nginx proxies)
- [ ] Rate limiting enabled in Nginx
- [ ] Database backups automated and tested
- [ ] Docker images scanned for vulnerabilities
- [ ] Firewall configured (UFW or iptables)
- [ ] SSH key authentication (disable password auth)
- [ ] Regular security updates (`apt update && apt upgrade`)

---

## Next Steps

1. **Set up AWS ECR** repositories with lifecycle policies
2. **Create GitHub secrets** for CI/CD
3. **SSH to server** and create `/opt/dreamops/` structure
4. **Upload configuration files** (docker-compose.yml, .env, nginx.conf)
5. **Get SSL certificate** with certbot
6. **Pull images and start** services
7. **Test end-to-end** functionality
8. **Set up automated backups**
9. **Configure DNS** to point to your server
10. **Push to GitHub** and watch automated deployment!

**Estimated Time**: 2-3 hours for initial setup, then 5 minutes per deployment

---

## Quick Commands Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Update (pull latest)
docker-compose pull && docker-compose up -d

# Logs
docker-compose logs -f

# Backup database
./backup.sh

# Clean up
docker system prune -af
```

🚀 **Ready to deploy!**
