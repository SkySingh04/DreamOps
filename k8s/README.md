# DreamOps Kubernetes Deployment

## Prerequisites

1. K3s cluster running
2. nginx ingress controller installed
3. cert-manager installed with letsencrypt-prod ClusterIssuer
4. AWS ECR access configured
5. DNS record: `oncall.frai.pro` → `37.27.111.47`

## Deployment Steps

### 1. Create Secrets

```bash
# Copy the example file
cp secrets.example.yaml secrets.yaml

# Edit with your actual values
nano secrets.yaml

# Apply secrets
kubectl apply -f secrets.yaml
```

### 2. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 3. Deploy Backend

```bash
kubectl apply -f backend-deployment.yaml
```

### 4. Deploy Frontend

```bash
kubectl apply -f frontend-deployment.yaml
```

### 5. Create Ingress

```bash
kubectl apply -f ingress.yaml
```

### 6. Verify Deployment

```bash
# Check all resources
kubectl get all -n dreamops

# Check ingress
kubectl get ingress -n dreamops

# Check certificate
kubectl get certificate -n dreamops

# Check pods
kubectl get pods -n dreamops

# View logs
kubectl logs -n dreamops -l app=dreamops-backend
kubectl logs -n dreamops -l app=dreamops-frontend
```

### 7. Test Access

```bash
# Wait for SSL certificate (1-2 minutes)
kubectl get certificate -n dreamops -w

# Test backend
curl https://oncall.frai.pro/health

# Test frontend
curl -I https://oncall.frai.pro/

# Test in browser
open https://oncall.frai.pro
```

## Update PagerDuty Webhook

Once deployed, update your PagerDuty webhook URL to:
```
https://oncall.frai.pro/webhook/pagerduty
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n dreamops
kubectl describe pod <pod-name> -n dreamops
```

### View Logs
```bash
kubectl logs -n dreamops -l app=dreamops-backend -f
kubectl logs -n dreamops -l app=dreamops-frontend -f
```

### Check Ingress
```bash
kubectl describe ingress dreamops-ingress -n dreamops
```

### Check Certificate
```bash
kubectl describe certificate dreamops-tls -n dreamops
kubectl get certificaterequest -n dreamops
```

### Restart Pods
```bash
kubectl rollout restart deployment/dreamops-backend -n dreamops
kubectl rollout restart deployment/dreamops-frontend -n dreamops
```

## Updating Images

The deployment uses `:latest` tag. To update:

```bash
# Pull new images from ECR
kubectl rollout restart deployment/dreamops-backend -n dreamops
kubectl rollout restart deployment/dreamops-frontend -n dreamops
```

Or use the CI/CD pipeline to automatically deploy on push to main.

## Configuration

### Backend Environment Variables

Modify in `backend-deployment.yaml`:
- `K8S_ENABLED`: Enable Kubernetes integration
- `K8S_NAMESPACE`: Namespace to monitor (default)
- `PAGERDUTY_ENABLED`: Enable PagerDuty webhook

### Frontend Environment Variables

Modify in `frontend-deployment.yaml`:
- `NEXT_PUBLIC_API_URL`: Backend API URL (cluster-internal)

### Resource Limits

Adjust in deployment files:
- Backend: 512Mi-1Gi memory, 250m-1000m CPU
- Frontend: 256Mi-512Mi memory, 100m-500m CPU

## Security

### RBAC Permissions

The backend ServiceAccount has permissions to:
- Read: pods, services, events, nodes, deployments
- Write: pods (delete, patch), deployments (patch, update)

### Secrets Management

All sensitive data is stored in Kubernetes secrets:
- `dreamops-secrets`: API keys, database URL, PagerDuty credentials

Never commit `secrets.yaml` with actual values!
