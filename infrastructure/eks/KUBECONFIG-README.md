# EKS Kubeconfig Setup Guide

## Prerequisites
1. AWS CLI installed
2. AWS credentials with access to the EKS cluster
3. kubectl installed

## Setup Instructions

### For Team Members

1. **Get AWS Credentials**
   - Obtain AWS access key and secret key for the `burner` profile from your team lead
   - These credentials need permissions to access the EKS cluster

2. **Configure AWS Profile**
   ```bash
   aws configure --profile burner
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: ap-south-1
   # Default output format: json
   ```

3. **Use the Provided Kubeconfig**
   ```bash
   # Option 1: Export the kubeconfig path
   export KUBECONFIG=/path/to/kubeconfig-oncall-agent-eks.yaml
   export AWS_PROFILE=burner
   
   # Option 2: Source the .env.eks file
   cd /path/to/oncall-agent/backend
   source .env.eks
   ```

4. **Verify Connection**
   ```bash
   kubectl get nodes
   kubectl get pods -n oncall-test-apps
   ```

## Cluster Details
- **Cluster Name**: oncall-agent-eks
- **Region**: ap-south-1 (Mumbai)
- **Context**: arn:aws:eks:ap-south-1:500489831186:cluster/oncall-agent-eks
- **Test Namespace**: oncall-test-apps

## Sharing the Kubeconfig

The kubeconfig file (`kubeconfig-oncall-agent-eks.yaml`) can be shared directly with team members. 
It contains the cluster endpoint and certificate but requires AWS credentials for authentication.

### Security Notes
- The kubeconfig uses AWS IAM for authentication
- Each user needs their own AWS credentials
- Never share AWS credentials, only the kubeconfig file
- The kubeconfig file itself doesn't contain any secrets

## Troubleshooting

### "You must be logged in to the server"
- Ensure AWS_PROFILE=burner is set
- Check AWS credentials: `aws sts get-caller-identity --profile burner`

### "Unable to connect to the server"
- Verify you're using the correct region (ap-south-1)
- Check if your IP is allowed in the EKS security groups
- Ensure your AWS credentials have the necessary EKS permissions