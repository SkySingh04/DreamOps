#!/bin/bash
set -e

echo "🚀 Deploying EKS monitoring with PagerDuty integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform is not installed${NC}"
    echo "Please install Terraform >= 1.5.0"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed${NC}"
    echo "Please install kubectl"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    echo "Please install AWS CLI"
    exit 1
fi

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}❌ terraform.tfvars not found${NC}"
    echo "Please copy terraform.tfvars.example to terraform.tfvars and configure it"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}🔐 Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Please configure AWS credentials with: aws configure"
    exit 1
fi

# Check EKS cluster access
echo -e "${YELLOW}🔍 Checking EKS cluster access...${NC}"
CLUSTER_NAME=$(grep 'project_name' terraform.tfvars | cut -d'"' -f2)-eks
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${YELLOW}⚠️  kubectl not configured for EKS cluster${NC}"
    echo "Updating kubeconfig..."
    aws eks update-kubeconfig --name $CLUSTER_NAME --region ap-south-1
fi

# Terraform deployment
echo -e "${YELLOW}🏗️  Initializing Terraform...${NC}"
terraform init

echo -e "${YELLOW}📋 Planning Terraform deployment...${NC}"
terraform plan

echo -e "${YELLOW}🚀 Applying Terraform configuration...${NC}"
read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Deployment cancelled${NC}"
    exit 1
fi

terraform apply -auto-approve

echo -e "${GREEN}✅ EKS monitoring deployment completed!${NC}"

# Post-deployment verification
echo -e "${YELLOW}🔍 Verifying deployment...${NC}"

# Check CloudWatch agent pods
echo "📊 Checking CloudWatch agent pods..."
kubectl get pods -n amazon-cloudwatch

# Check SNS topic
echo "📢 Checking SNS topic..."
aws sns list-topics --query 'Topics[?contains(TopicArn, `eks-alerts`)]'

# Check CloudWatch alarms
echo "⚠️  Checking CloudWatch alarms..."
aws cloudwatch describe-alarms --alarm-name-prefix "oncall-agent-eks" --query 'MetricAlarms[].{Name:AlarmName,State:StateValue}'

echo -e "${GREEN}🎉 EKS to PagerDuty monitoring is now active!${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Deploy test applications: ./deploy-sample-apps.sh"
echo "2. Monitor CloudWatch dashboard: oncall-agent-eks-dashboard"
echo "3. Test PagerDuty integration by triggering alerts"
echo "4. Check logs: kubectl logs -n amazon-cloudwatch -l name=cloudwatch-agent"

echo ""
echo -e "${GREEN}🚨 Alert Types Configured:${NC}"
echo "• Pod Restarts (>5 in 5min) → Critical"
echo "• Node Not Ready (<2 nodes) → Critical" 
echo "• Container Memory (>90%) → Critical"
echo "• Cluster CPU (>80%) → High"
echo "• Cluster Memory (>80%) → High"
echo "• Failed Pods (>3 restarts) → High"