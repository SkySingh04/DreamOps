# DreamOps Bare-Metal K3s Deployment Guide

This guide covers deploying DreamOps on the bare-metal K3s cluster with Authentik reverse proxy for authentication.

## Architecture Overview

- **Cluster**: Bare-metal K3s cluster (2 nodes)
- **Authentication**: Authentik reverse proxy (handles all auth)
- **Database**: Neon PostgreSQL (managed, separate from cluster)
- **Storage**: Local path provisioner (K3s default)
- **Ingress**: Traefik (K3s default) or NGINX

## Prerequisites

1. **Access to bare-metal K3s cluster**
   ```bash
   kubectl config use-context bare-metal
   kubectl get nodes
   ```

2. **Neon Database**
   - Production database already configured
   - Connection string from `.env.production`

3. **Authentik Setup**
   - Authentik deployed and configured
   - Application proxy configured for DreamOps
   - User headers configured

4. **Required Secrets**
   - Anthropic API key
   - PagerDuty credentials
   - Database connection string

## Deployment Architecture

```
Internet
    ↓
Authentik (Reverse Proxy + Auth)
    ↓
DreamOps Frontend (Next.js)
    ↓
DreamOps Backend (FastAPI)
    ↓
Neon PostgreSQL (External)
```

## Step 1: Create Namespace

```bash
kubectl create namespace dreamops
```

## Step 2: Create Secrets

Create the secrets file:

```bash
# Create secrets
kubectl create secret generic dreamops-secrets -n dreamops \
  --from-literal=anthropic-api-key='YOUR_ANTHROPIC_API_KEY' \
  --from-literal=database-url='YOUR_NEON_DATABASE_URL' \
  --from-literal=pagerduty-api-key='YOUR_PAGERDUTY_API_KEY' \
  --from-literal=pagerduty-webhook-secret='YOUR_WEBHOOK_SECRET' \
  --from-literal=pagerduty-user-email='YOUR_EMAIL'
```

## Step 3: Deploy Backend

Create `backend-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dreamops-backend
  namespace: dreamops
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dreamops-backend
  template:
    metadata:
      labels:
        app: dreamops-backend
    spec:
      containers:
      - name: backend
        image: YOUR_REGISTRY/dreamops-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: dreamops-secrets
              key: anthropic-api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dreamops-secrets
              key: database-url
        - name: PAGERDUTY_API_KEY
          valueFrom:
            secretKeyRef:
              name: dreamops-secrets
              key: pagerduty-api-key
        - name: PAGERDUTY_WEBHOOK_SECRET
          valueFrom:
            secretKeyRef:
              name: dreamops-secrets
              key: pagerduty-webhook-secret
        - name: PAGERDUTY_USER_EMAIL
          valueFrom:
            secretKeyRef:
              name: dreamops-secrets
              key: pagerduty-user-email
        - name: ENVIRONMENT
          value: "production"
        - name: API_HOST
          value: "0.0.0.0"
        - name: API_PORT
          value: "8000"
        - name: CORS_ORIGINS
          value: "https://dreamops.finalroundai.com"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: dreamops-backend
  namespace: dreamops
spec:
  selector:
    app: dreamops-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

Apply:
```bash
kubectl apply -f backend-deployment.yaml
```

## Step 4: Deploy Frontend

Create `frontend-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dreamops-frontend
  namespace: dreamops
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dreamops-frontend
  template:
    metadata:
      labels:
        app: dreamops-frontend
    spec:
      containers:
      - name: frontend
        image: YOUR_REGISTRY/dreamops-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "http://dreamops-backend:8000"
        - name: NEXT_PUBLIC_WS_URL
          value: "ws://dreamops-backend:8000"
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: dreamops-secrets
              key: database-url
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: dreamops-frontend
  namespace: dreamops
spec:
  selector:
    app: dreamops-frontend
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
```

Apply:
```bash
kubectl apply -f frontend-deployment.yaml
```

## Step 5: Configure Authentik Proxy

### In Authentik:

1. **Create Provider**:
   - Type: Proxy Provider
   - Name: DreamOps
   - External host: `https://dreamops.finalroundai.com`
   - Internal host: `http://dreamops-frontend.dreamops.svc.cluster.local:3000`
   - Forward auth (single application): Enable

2. **Configure Headers**:
   Add these headers to pass user identity:
   ```
   X-Authentik-Username: {{ user.username }}
   X-Authentik-Email: {{ user.email }}
   X-Authentik-Name: {{ user.name }}
   X-Authentik-Groups: {{ user.groups }}
   ```

3. **Create Application**:
   - Name: DreamOps
   - Slug: dreamops
   - Provider: DreamOps (from step 1)

4. **Update Outpost**:
   - Add DreamOps application to your outpost
   - Deploy/restart outpost

## Step 6: Ingress (Alternative to Authentik)

If using separate ingress (not recommended - use Authentik proxy):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dreamops-ingress
  namespace: dreamops
  annotations:
    kubernetes.io/ingress.class: traefik
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - dreamops.finalroundai.com
    secretName: dreamops-tls
  rules:
  - host: dreamops.finalroundai.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dreamops-frontend
            port:
              number: 3000
```

## Step 7: Database Migrations

Run migrations from your local machine:

```bash
cd frontend
cp .env.production .env
npm run db:migrate:production
```

## Step 8: Verify Deployment

```bash
# Check pods
kubectl get pods -n dreamops

# Check services
kubectl get svc -n dreamops

# Check logs
kubectl logs -n dreamops -l app=dreamops-backend
kubectl logs -n dreamops -l app=dreamops-frontend

# Test backend health
kubectl port-forward -n dreamops svc/dreamops-backend 8000:8000
curl http://localhost:8000/health

# Test frontend
kubectl port-forward -n dreamops svc/dreamops-frontend 3000:3000
curl http://localhost:3000
```

## Step 9: Configure PagerDuty Webhook

In PagerDuty:
1. Go to Integrations → Generic Webhooks
2. Add webhook URL: `https://dreamops.finalroundai.com/webhook/pagerduty`
3. Test the webhook

## Building Docker Images

### Backend Image

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY main.py .
COPY api_server.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "python", "api_server.py"]
```

Build and push:
```bash
cd backend
docker build -t YOUR_REGISTRY/dreamops-backend:latest .
docker push YOUR_REGISTRY/dreamops-backend:latest
```

### Frontend Image

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy application code
COPY . .

# Build application
RUN npm run build:production

FROM node:20-alpine AS runner

WORKDIR /app

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "start"]
```

Build and push:
```bash
cd frontend
docker build -t YOUR_REGISTRY/dreamops-frontend:latest .
docker push YOUR_REGISTRY/dreamops-frontend:latest
```

## Monitoring and Logs

### View Logs

```bash
# Backend logs
kubectl logs -n dreamops -l app=dreamops-backend -f

# Frontend logs
kubectl logs -n dreamops -l app=dreamops-frontend -f

# All dreamops logs
kubectl logs -n dreamops --all-containers=true -f
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n dreamops

# Node resource usage
kubectl top nodes
```

## Scaling

```bash
# Scale backend
kubectl scale deployment dreamops-backend -n dreamops --replicas=3

# Scale frontend
kubectl scale deployment dreamops-frontend -n dreamops --replicas=3
```

## Troubleshooting

### Pod Not Starting

```bash
# Describe pod
kubectl describe pod -n dreamops <pod-name>

# Check events
kubectl get events -n dreamops --sort-by='.lastTimestamp'
```

### Database Connection Issues

```bash
# Test database connection from pod
kubectl exec -it -n dreamops <backend-pod> -- python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('YOUR_DATABASE_URL')
    print(await conn.fetchval('SELECT version()'))
    await conn.close()
asyncio.run(test())
"
```

### Authentik Not Passing Headers

Check Authentik logs and verify:
1. Outpost is running and healthy
2. Provider is configured correctly
3. Application is assigned to outpost
4. Headers are configured in provider settings

## Updating Deployment

### Update Backend

```bash
# Build new image
cd backend
docker build -t YOUR_REGISTRY/dreamops-backend:v1.1.0 .
docker push YOUR_REGISTRY/dreamops-backend:v1.1.0

# Update deployment
kubectl set image deployment/dreamops-backend -n dreamops \
  backend=YOUR_REGISTRY/dreamops-backend:v1.1.0

# Verify rollout
kubectl rollout status deployment/dreamops-backend -n dreamops
```

### Update Frontend

```bash
# Build new image
cd frontend
docker build -t YOUR_REGISTRY/dreamops-frontend:v1.1.0 .
docker push YOUR_REGISTRY/dreamops-frontend:v1.1.0

# Update deployment
kubectl set image deployment/dreamops-frontend -n dreamops \
  frontend=YOUR_REGISTRY/dreamops-frontend:v1.1.0

# Verify rollout
kubectl rollout status deployment/dreamops-frontend -n dreamops
```

## Rollback

```bash
# Rollback backend
kubectl rollout undo deployment/dreamops-backend -n dreamops

# Rollback frontend
kubectl rollout undo deployment/dreamops-frontend -n dreamops

# Rollback to specific revision
kubectl rollout undo deployment/dreamops-backend -n dreamops --to-revision=2
```

## Cleanup

To remove the entire deployment:

```bash
# Delete namespace (removes all resources)
kubectl delete namespace dreamops

# Or delete individual resources
kubectl delete -f backend-deployment.yaml
kubectl delete -f frontend-deployment.yaml
kubectl delete secret dreamops-secrets -n dreamops
```

## Security Checklist

- [ ] Authentik is properly configured and securing the application
- [ ] All secrets are stored in Kubernetes secrets (not hardcoded)
- [ ] Database connection uses SSL (`?sslmode=require`)
- [ ] Resource limits are set for all containers
- [ ] Network policies are configured (optional, recommended)
- [ ] RBAC is properly configured
- [ ] Images are scanned for vulnerabilities
- [ ] Pod security policies/standards are applied

## Bare-Metal Cluster Specifics

### K3s Features Used
- **Traefik Ingress**: Default K3s ingress controller
- **Local Path Provisioner**: For persistent storage (if needed)
- **ServiceLB**: Load balancer implementation

### Cluster Information
- **Control Plane**: ip-37-27-111-47
- **Worker**: k3s-worker
- **Version**: v1.33.4+k3s1

### Node Selectors (Optional)

To ensure pods run on specific nodes:

```yaml
spec:
  nodeSelector:
    kubernetes.io/hostname: k3s-worker
```

## Support

For issues:
1. Check pod logs: `kubectl logs -n dreamops <pod-name>`
2. Check pod status: `kubectl describe pod -n dreamops <pod-name>`
3. Verify secrets: `kubectl get secrets -n dreamops`
4. Test connectivity: `kubectl exec -it -n dreamops <pod-name> -- /bin/sh`

## Next Steps

1. Set up monitoring (Prometheus/Grafana)
2. Configure backups for database
3. Set up alerting for critical issues
4. Implement CI/CD pipeline
5. Configure horizontal pod autoscaling
