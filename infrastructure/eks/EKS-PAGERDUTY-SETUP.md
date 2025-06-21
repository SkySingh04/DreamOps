# EKS to PagerDuty Automatic Monitoring Setup

This guide sets up comprehensive monitoring for your EKS cluster with automatic PagerDuty alerts.

## 🚀 Architecture Overview

```
EKS Issues → CloudWatch Container Insights → CloudWatch Alarms → SNS Topic → PagerDuty → Your Phone + AI Agent
```

## 📋 Prerequisites

1. **EKS Cluster**: Your `oncall-agent-eks` cluster must be running
2. **PagerDuty Account**: With a service configured for CloudWatch integration
3. **AWS Permissions**: CloudWatch, SNS, and EKS permissions
4. **Terraform**: >= 1.5.0

## 🛠️ Setup Instructions

### Step 1: Configure PagerDuty Service

1. **Login to PagerDuty**
2. **Navigate to Services**
3. **Create/Select your service** (e.g., "EKS Monitoring")
4. **Go to Integrations tab**
5. **Add Integration → Amazon CloudWatch**
6. **Copy the Integration URL** (format: `https://events.pagerduty.com/integration/xxx/enqueue`)

### Step 2: Update Terraform Configuration

1. **Copy the example file**:
   ```bash
   cd infrastructure/eks
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars**:
   ```hcl
   # Your existing config
   project_name = "oncall-agent"
   environment  = "testing"
   aws_region   = "ap-south-1"
   vpc_cidr     = "10.1.0.0/16"
   
   # Add PagerDuty integration
   pagerduty_endpoint = "https://events.pagerduty.com/integration/YOUR_KEY_HERE/enqueue"
   
   # Optional: Email for testing
   alarm_email = "your-email@example.com"
   ```

### Step 3: Deploy the Monitoring Stack

```bash
cd infrastructure/eks

# Initialize Terraform (if not done)
terraform init

# Plan the deployment
terraform plan

# Apply the monitoring configuration
terraform apply
```

This will deploy:
- ✅ CloudWatch Container Insights agents
- ✅ Fluent Bit for log collection  
- ✅ CloudWatch alarms for critical EKS metrics
- ✅ SNS topic connected to PagerDuty
- ✅ CloudWatch dashboard for EKS monitoring

### Step 4: Test the Integration

1. **Deploy test applications**:
   ```bash
   ./deploy-sample-apps.sh
   ```

2. **Trigger alerts manually**:
   ```bash
   # Force a pod to crash
   kubectl scale deployment config-missing-app -n test-apps --replicas=5
   
   # Check alarm status
   aws cloudwatch describe-alarms --alarm-names "oncall-agent-eks-pod-restarts"
   ```

3. **Verify PagerDuty receives alerts**:
   - Check your PagerDuty dashboard
   - Verify incidents are created
   - Test phone/SMS notifications

## 📊 Monitoring Coverage

### Critical Alerts (Will page you)

| Alert | Threshold | Description |
|-------|-----------|-------------|
| **Pod Restarts** | >5 restarts in 5min | CrashLoopBackOff, OOMKilled, etc. |
| **Node Not Ready** | <2 nodes ready | Node failures, network issues |
| **Container Memory** | >90% memory usage | Memory pressure, potential OOM |

### High Priority Alerts

| Alert | Threshold | Description |
|-------|-----------|-------------|
| **CPU High** | >80% for 10min | High cluster CPU utilization |
| **Memory High** | >80% for 10min | High cluster memory utilization |
| **Failed Pods** | >3 container restarts | Repeated pod failures |

### Logs and Metrics

- **Application Logs**: `/aws/containerinsights/oncall-agent-eks/application`
- **Host Logs**: `/aws/containerinsights/oncall-agent-eks/host`  
- **Dataplane Logs**: `/aws/containerinsights/oncall-agent-eks/dataplane`
- **Dashboard**: `oncall-agent-eks-dashboard` in CloudWatch

## 🔧 Customization

### Adjusting Alert Thresholds

Edit `infrastructure/eks/eks-monitoring.tf`:

```hcl
# Example: Change CPU alert threshold
resource "aws_cloudwatch_metric_alarm" "eks_cpu_high" {
  threshold = "70"  # Change from 80 to 70
  # ... rest of config
}
```

### Adding Custom Alerts

Add new alarms to `eks-monitoring.tf`:

```hcl
resource "aws_cloudwatch_metric_alarm" "custom_alert" {
  alarm_name          = "${var.project_name}-custom-alert"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "your_metric"
  namespace           = "ContainerInsights"
  # ... additional config
}
```

## 🚨 Alert Types You'll Receive

### 1. Pod CrashLoopBackOff
**Trigger**: Pod restarts >5 times in 5 minutes
**Common Causes**: 
- Missing ConfigMaps/Secrets
- Image pull failures  
- Application startup errors
- Resource limits hit

### 2. OOM (Out of Memory) Kills
**Trigger**: Container memory >90%
**Common Causes**:
- Memory leaks
- Insufficient memory limits
- Sudden traffic spikes

### 3. Node Issues
**Trigger**: <2 nodes in Ready state
**Common Causes**:
- EC2 instance failures
- Network connectivity issues
- kubelet crashes

### 4. High Resource Usage
**Trigger**: CPU/Memory >80% for 10+ minutes
**Common Causes**:
- Traffic spikes
- Resource-intensive workloads
- Insufficient cluster capacity

## 🔍 Troubleshooting

### Container Insights Not Showing Data

1. **Check agent pods**:
   ```bash
   kubectl get pods -n amazon-cloudwatch
   ```

2. **Check agent logs**:
   ```bash
   kubectl logs -n amazon-cloudwatch -l name=cloudwatch-agent
   kubectl logs -n amazon-cloudwatch -l k8s-app=fluent-bit
   ```

3. **Verify IAM permissions**:
   ```bash
   aws sts get-caller-identity
   # Ensure your role has CloudWatch permissions
   ```

### PagerDuty Not Receiving Alerts

1. **Test SNS topic manually**:
   ```bash
   aws sns publish \
     --topic-arn "arn:aws:sns:ap-south-1:YOUR_ACCOUNT:oncall-agent-eks-alerts" \
     --message "Test alert from EKS monitoring"
   ```

2. **Check SNS subscription**:
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn "arn:aws:sns:ap-south-1:YOUR_ACCOUNT:oncall-agent-eks-alerts"
   ```

3. **Verify PagerDuty integration URL** in terraform.tfvars

### Alarms Not Triggering

1. **Check CloudWatch metrics**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace ContainerInsights \
     --metric-name cluster_cpu_utilization \
     --dimensions Name=ClusterName,Value=oncall-agent-eks \
     --start-time 2023-01-01T00:00:00Z \
     --end-time 2023-01-01T23:59:59Z \
     --period 300 \
     --statistics Average
   ```

2. **Review alarm history**:
   ```bash
   aws cloudwatch describe-alarm-history \
     --alarm-name oncall-agent-eks-cpu-high
   ```

## 🎯 Next Steps

1. **Integrate with your oncall agent**: The alerts will trigger your PagerDuty service, which can then webhook to your oncall agent API
2. **Set up escalation policies**: Configure PagerDuty escalation rules
3. **Add custom metrics**: Extend monitoring for your specific applications
4. **Tune alert thresholds**: Adjust based on your traffic patterns

## 📝 Important Notes

- **Cost**: Container Insights and CloudWatch logs will incur AWS charges
- **Retention**: Logs are retained for 7 days (configurable)
- **Performance**: Monitoring agents use ~200MB RAM and 200m CPU per node
- **Security**: All communication uses IAM roles and service accounts

## 🆘 Support

If you encounter issues:
1. Check the CloudWatch agent and Fluent Bit logs
2. Verify your PagerDuty integration URL
3. Test SNS topic manually
4. Review IAM permissions for the service accounts

Your EKS cluster is now fully monitored with automatic PagerDuty alerting! 🎉