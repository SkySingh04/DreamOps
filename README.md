# Oncall AI Agent

An intelligent AI-powered oncall agent that automatically triages and resolves incidents using Claude AI and Model Context Protocol (MCP) integrations. The agent can debug Kubernetes issues, analyze logs, and suggest remediation steps.

## 🚀 Features

- **AI-Powered Analysis**: Uses Claude to intelligently analyze alerts and suggest solutions
- **Kubernetes Integration**: Automatically debugs pod crashes, OOM issues, and configuration problems
- **MCP Architecture**: Extensible integration system for connecting to various tools (Grafana, Slack, PagerDuty, etc.)
- **Pattern Detection**: Recognizes common incident patterns and applies appropriate debugging strategies
- **Safety Mechanisms**: Configurable automation levels with safety checks for destructive operations
- **Real-time Processing**: Async architecture for handling multiple incidents concurrently
- **REST API**: FastAPI backend with automatic documentation
- **CI/CD Ready**: GitHub Actions workflows for automated deployment
- **AWS Native**: Terraform modules for ECS, CloudFront, and EKS

## 🏗️ Architecture

```
oncall-agent/
├── backend/                    # Python AI agent backend
│   ├── src/                   # Source code
│   │   └── oncall_agent/      # Main package
│   │       ├── api.py         # FastAPI REST API
│   │       ├── agent.py       # Core agent logic
│   │       ├── config.py      # Configuration
│   │       └── mcp_integrations/  # MCP integrations
│   ├── tests/                 # Test files  
│   ├── examples/              # Example scripts
│   ├── main.py               # CLI entry point
│   └── Dockerfile.prod       # Production Docker image
├── frontend/                  # Next.js SaaS web interface
│   ├── app/                  # App router pages
│   ├── components/           # React components
│   └── lib/                  # Utilities
├── infrastructure/           # AWS deployment configs
│   ├── terraform/           # ECS/CloudFront infrastructure
│   └── eks/                # EKS cluster for testing
├── .github/workflows/       # CI/CD pipelines
└── docker-compose.yml
```

### System Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Alert Source  │────▶│  Oncall AI Agent │────▶│  Claude AI API  │
│  (PagerDuty)    │     │                  │     │   (Analysis)    │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │    MCP Integrations      │
                    ├──────────────────────────┤
                    │ • Kubernetes             │
                    │ • GitHub                 │
                    │ • Grafana (planned)      │
                    │ • Slack (planned)        │
                    └──────────────────────────┘
```

### AWS Infrastructure Overview

The deployment creates:
- **VPC** with public/private subnets across 2 AZs
- **ECS Fargate** cluster for the backend
- **Application Load Balancer** for backend API
- **S3 + CloudFront** for frontend hosting
- **ECR** for Docker image storage
- **CloudWatch** for monitoring and alarms
- **Secrets Manager** for sensitive configuration

## 📋 Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Anthropic API key
- Kubernetes cluster (for K8s integration)
- AWS account (for deployment)
- Terraform >= 1.5.0 (for infrastructure deployment)

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/oncall-agent.git
cd oncall-agent
```

### 2. Backend Setup

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup (Optional)

```bash
cd frontend
npm install
```

## 🔧 Configuration

Key environment variables in `backend/.env`:

```env
# Core settings
ANTHROPIC_API_KEY=your-api-key
LOG_LEVEL=INFO

# Kubernetes integration
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false

# GitHub integration (optional)
GITHUB_TOKEN=your-github-token
```

## 🚀 Usage

### Quick Start Demo

```bash
cd backend
uv run python main.py
```

This runs a simulated alert through the agent to demonstrate its capabilities.

### API Server

```bash
cd backend
uv run uvicorn src.oncall_agent.api:app --host 0.0.0.0 --port 8000

# View API docs
open http://localhost:8000/docs
```

### API Endpoints

- `POST /alerts` - Submit a new alert for processing
- `GET /health` - Health check endpoint
- `GET /integrations` - List available MCP integrations
- `POST /integrations/{name}/health` - Check integration health

### Docker

```bash
# Development
docker-compose up

# Production
docker build -t oncall-agent -f backend/Dockerfile.prod backend/
docker run -p 8000:8000 --env-file backend/.env oncall-agent
```

## 🧪 Testing

### Local Kubernetes Testing

1. **Create a test cluster**:
```bash
kind create cluster --name oncall-test
```

2. **Deploy a broken pod**:
```bash
kubectl apply -f backend/broken-app.yaml
```

3. **Run the agent**:
```bash
cd backend
uv run python main.py
```

### EKS Testing (Advanced)

For testing with a real AWS EKS cluster with multiple failure scenarios:

```bash
# Deploy EKS infrastructure
cd infrastructure/eks
terraform init
terraform apply

# Deploy test apps
./deploy-sample-apps.sh

# Run test scenarios
cd backend
uv run python tests/test_eks_scenarios.py all
```

### Running Tests

```bash
cd backend

# Run all tests
uv run pytest tests/

# Run specific test
uv run pytest tests/test_kubernetes_integration.py

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## 🔌 MCP Integrations

### Available Integrations

1. **Kubernetes** - Debugs pod crashes, OOM issues, and config problems
2. **GitHub** - Fetches context from repositories and creates incident issues (🚀 **Auto-starts MCP server**)
3. **Notion** - Creates incident documentation (if configured)

### 🤖 GitHub MCP Integration - Automatic Startup

The GitHub MCP integration features **automatic server management** - no manual setup required!

**How it works:**
1. When you enable GitHub integration (`--github-integration`), the agent automatically:
   - 🚀 Starts the GitHub MCP server as a subprocess
   - 🔗 Establishes MCP protocol connection via JSON-RPC 2.0
   - 🏓 Performs health checks to ensure connectivity
   - 🧹 Automatically cleans up the server process on shutdown

**Configuration:**
```bash
# Required in .env file
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_MCP_SERVER_PATH=../github-mcp-server/github-mcp-server

# Optional settings
GITHUB_MCP_HOST=localhost
GITHUB_MCP_PORT=8081
```

**Usage:**
```bash
# GitHub MCP server starts automatically with this command
uv run python simulate_pagerduty_alert.py pod_crash --github-integration

# Or with the main demo
uv run python main.py  # If GitHub token is configured
```

**Capabilities:**
- 📊 Fetch recent commits and repository context
- 🔍 Search code for error patterns and related issues
- 📝 Create GitHub issues for incident tracking
- ⚡ Check GitHub Actions workflow status
- 📁 Access repository files and documentation

**Benefits:**
- ✅ Zero manual server management
- ✅ Automatic process lifecycle handling  
- ✅ Full GitHub API access via MCP protocol
- ✅ Clean resource cleanup and error handling

### Adding New Integrations

1. Create a new file in `backend/src/oncall_agent/mcp_integrations/`
2. Extend the `MCPIntegration` base class:

```python
from src.oncall_agent.mcp_integrations.base import MCPIntegration

class MyIntegration(MCPIntegration):
    def __init__(self):
        super().__init__(name="my_integration")
    
    async def connect(self):
        # Establish connection
        pass
    
    async def fetch_context(self, params: Dict[str, Any]):
        # Retrieve relevant information
        pass
    
    # Implement other required methods
```

## 🚀 AWS Deployment Guide

### Step 1: Prepare AWS Secrets

Create secrets in AWS Secrets Manager:

```bash
# Store Anthropic API key
aws secretsmanager create-secret \
  --name oncall-agent/anthropic-api-key \
  --secret-string "YOUR_ANTHROPIC_API_KEY"

# Store Kubernetes config (if using K8s integration)
aws secretsmanager create-secret \
  --name oncall-agent/k8s-config \
  --secret-string file://~/.kube/config
```

### Step 2: Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets → Actions):

1. **AWS_ACCESS_KEY_ID** - AWS access key for deployment
2. **AWS_SECRET_ACCESS_KEY** - AWS secret key  
3. **ANTHROPIC_API_KEY** - Your Anthropic API key
4. **CLOUDFRONT_DISTRIBUTION_ID** - CloudFront ID (add after initial deployment)
5. **REACT_APP_API_URL** - Backend API URL (add after initial deployment)

### Step 3: Deploy Infrastructure with Terraform

1. Initialize Terraform:
```bash
cd infrastructure/terraform
terraform init
```

2. Create a `terraform.tfvars` file:
```hcl
project_name = "oncall-agent"
environment  = "production"
aws_region   = "us-east-1"

# Replace with your secret ARNs from Step 1
anthropic_api_key_arn = "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:oncall-agent/anthropic-api-key-XXXXX"
k8s_config_secret_arn = "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:oncall-agent/k8s-config-XXXXX"

alarm_email = "your-email@example.com"
```

3. Deploy:
```bash
terraform plan
terraform apply
```

4. Note the outputs:
   - `backend_api_url`: Add as `REACT_APP_API_URL` in GitHub Secrets
   - `cloudfront_distribution_id`: Add as `CLOUDFRONT_DISTRIBUTION_ID` in GitHub Secrets

### Step 4: Initial Backend Deployment

Build and push the initial Docker image:

```bash
cd backend

# Get ECR login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t oncall-agent-backend -f Dockerfile.prod .
docker tag oncall-agent-backend:latest \
  YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/oncall-agent-backend:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/oncall-agent-backend:latest
```

### Step 5: Deploy Frontend

```bash
cd frontend
npm install
npm run build

# Sync to S3
aws s3 sync build/ s3://oncall-agent-frontend-production --delete

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Step 6: Verify Deployment

1. Check ECS service:
```bash
aws ecs describe-services \
  --cluster oncall-agent-cluster \
  --services oncall-agent-backend-service
```

2. Test the API:
```bash
curl http://YOUR_ALB_DNS_NAME/health
```

### Automated CI/CD

After initial setup, the GitHub Actions workflows will automatically:
- Run tests and linting on pull requests
- Deploy to AWS when merging to main branch

Workflows are configured in:
- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`

## 🛠️ Development

### ⚠️ Pre-commit Checklist

**ALWAYS run these before committing:**

```bash
cd backend

# 1. Fix code style
uv run ruff check . --fix

# 2. Check types (optional - legacy issues exist)
uv run mypy . --ignore-missing-imports

# 3. Run tests
uv run pytest tests/

# 4. Verify it works
uv run python main.py
```

### Quick Validation

```bash
cd backend
./scripts/validate.sh
```

### Development Workflow

1. Create feature branch
2. Make changes
3. Run validation (see above)
4. Submit PR with tests

## 📊 Example Output

```
🚨 ALERT RECEIVED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alert ID: K8S-001
Service: payment-service
Description: Pod payment-service-7d9f8b6c5-x2n4m is in CrashLoopBackOff state

🔍 DETECTING ALERT TYPE
✓ Detected Kubernetes alert type: pod_crash

📊 GATHERING KUBERNETES CONTEXT
✓ Found pod in namespace: default
✓ Container State: Waiting (CrashLoopBackOff)
✓ Restart Count: 5
✓ Recent Logs: ERROR: Configuration file /config/app.conf not found!

🤖 CLAUDE AI ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Root Cause
Missing ConfigMap containing application configuration

## Immediate Actions
1. Check if ConfigMap exists:
   kubectl get configmap payment-config -n default

2. Create ConfigMap if missing:
   kubectl create configmap payment-config --from-file=app.conf

## Resolution Confidence: HIGH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 🏃 Quick Reference

```bash
# Backend
uv run python main.py                    # Run demo
uv run uvicorn src.oncall_agent.api:app # Start API
uv run pytest tests/                     # Run tests
uv run ruff check . --fix               # Fix linting

# Frontend  
npm run dev                              # Start dev server
npm run build                            # Build for production
npm test                                 # Run tests

# Docker
docker-compose up                        # Run full stack
docker build -f backend/Dockerfile.prod  # Build backend

# Validation
cd backend && ./scripts/validate.sh      # Run all checks
```

## 📊 Monitoring & Operations

### CloudWatch Monitoring
- **Dashboards**: View metrics in AWS Console
- **Alarms**: CPU and memory alerts via email
- **Logs**: Application logs in CloudWatch Logs

### Cost Optimization
- Use Fargate Spot for non-production
- Set auto-scaling policies
- Use S3 lifecycle policies for logs
- Consider Lambda for intermittent loads

### Troubleshooting

**ECS Task Fails to Start**
- Check CloudWatch Logs
- Verify secrets are accessible
- Ensure Docker image is built correctly

**Frontend Not Loading**
- Check CloudFront status
- Verify S3 bucket policy
- Check browser console for CORS

**High AWS Costs**
- Review CloudWatch metrics
- Check for unused resources
- Enable cost allocation tags

## 🔒 Security

- **Never commit** API keys or secrets
- **Use AWS Secrets Manager** for production
- **Enable audit logging** for all automated actions
- **Set `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false`** by default
- **Security scanning** runs automatically on every PR
- **Use IAM roles** instead of access keys where possible
- **Enable MFA** for AWS accounts
- **Regularly rotate** secrets and access keys
- **Enable GuardDuty** for threat detection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. **Run all validation checks**
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [AGNO Framework](https://github.com/agno-ai/agno)
- Powered by [Claude AI](https://www.anthropic.com/claude)
- Uses [Model Context Protocol](https://modelcontextprotocol.io/)

---

Built with ❤️ by the Oncall AI Team