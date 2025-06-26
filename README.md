# DreamOps

An intelligent AI-powered incident response and infrastructure management platform that automatically triages and resolves incidents using Claude AI and Model Context Protocol (MCP) integrations. The platform can debug Kubernetes issues, analyze logs, and suggest remediation steps. Dream easy while AI takes your on-call duty.

## 🚀 Features

### Core Capabilities
- **AI-Powered Analysis**: Uses Claude to intelligently analyze alerts and suggest solutions
- **Kubernetes Integration**: Automatically debugs pod crashes, OOM issues, and configuration problems
- **MCP Architecture**: Extensible integration system for connecting to various tools (Grafana, Slack, PagerDuty, etc.)
- **Pattern Detection**: Recognizes common incident patterns and applies appropriate debugging strategies
- **Safety Mechanisms**: Configurable automation levels with safety checks for destructive operations
- **Real-time Processing**: Async architecture for handling multiple incidents concurrently

### API & Web Interface
- **REST API**: FastAPI backend with automatic documentation
- **SaaS Frontend**: Next.js web interface with real-time dashboard
- **WebSocket Support**: Real-time metrics and incident updates
- **Comprehensive Endpoints**: Full incident management, analytics, and monitoring

### Deployment & DevOps
- **CI/CD Ready**: GitHub Actions workflows for automated deployment
- **AWS Native**: Terraform modules for ECS, CloudFront, and EKS
- **Container Ready**: Docker support with production-ready images
- **Monitoring Integration**: Built-in CloudWatch, PagerDuty, and custom monitoring

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
├── fuck_kubernetes.sh       # Testing script for simulating K8s issues
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
                    │ • Grafana                │
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
npm run dev  # Starts on http://localhost:3000
```

#### Default Authentication Credentials

The frontend comes with pre-filled authentication credentials for easy testing:

**Sign In (Admin Account):**
- Email: `admin@oncall.ai`
- Password: `AdminPass123!`

**Sign Up (Random Test User):**
- Email: Auto-generated (e.g., `user1234@example.com`)
- Password: Auto-generated (e.g., `TestPass1234!`)

These credentials are automatically filled in the login forms for quick access during development and testing.

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

# Grafana integration (optional)
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your-grafana-api-key

# Notion integration (optional)  
NOTION_TOKEN=your-notion-token

# PagerDuty integration
PAGERDUTY_API_KEY=your-api-key-here
PAGERDUTY_USER_EMAIL=your-email@company.com
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
```

## 📚 Database Setup

### Setting up Three Separate Neon Databases

The platform uses separate databases for different environments to ensure complete data isolation:

#### Step 1: Create Neon Projects

1. Go to [neon.tech](https://neon.tech) and create 3 separate projects:
   - `dreamops-local` - For local development
   - `dreamops-staging` - For staging/testing
   - `dreamops-prod` - For production

2. For each project:
   - Region: Choose closest to you (e.g., US East, EU Central)
   - Database name: `oncall_agent`
   - Branch: Keep main branch

#### Step 2: Configure Environment Files

**Backend Configuration:**

Create these files in your `backend/` directory:

```bash
# .env.local (for local development)
DATABASE_URL=postgresql://[your-local-neon-connection-string]
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=DEBUG
ENVIRONMENT=local

# .env.staging
DATABASE_URL=postgresql://[your-staging-neon-connection-string]
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=INFO
ENVIRONMENT=staging

# .env.production
DATABASE_URL=postgresql://[your-prod-neon-connection-string]
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=INFO
ENVIRONMENT=production
```

**Frontend Configuration:**

Create these files in your `frontend/` directory:

```bash
# .env.local
POSTGRES_URL=postgresql://[your-local-neon-connection-string]
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=local

# .env.staging
POSTGRES_URL=postgresql://[your-staging-neon-connection-string]
NEXT_PUBLIC_API_URL=https://api-staging.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=staging

# .env.production
POSTGRES_URL=postgresql://[your-prod-neon-connection-string]
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=production
```

#### Step 3: Database Migrations

Run migrations for each environment:

```bash
cd frontend

# Local
npm run db:migrate:local      # Auto-migrates

# Staging
npm run db:migrate:staging    # Auto-migrates

# Production (be careful!)
npm run db:migrate:production # Requires confirmation
```

#### Step 4: Database Testing

**Automated Testing:**
```bash
cd frontend
npm run test:db  # Tests all database connections
```

**Manual Testing with psql:**
```bash
# Test each connection
psql "your-local-connection-string" -c "SELECT current_database(), 'LOCAL' as env;"
psql "your-staging-connection-string" -c "SELECT current_database(), 'STAGING' as env;"
psql "your-prod-connection-string" -c "SELECT current_database(), 'PRODUCTION' as env;"
```

**Using Drizzle Studio:**
```bash
cd frontend

# View LOCAL database
npm run db:studio              # Opens at http://localhost:4983

# View STAGING database
POSTGRES_URL="your-staging-connection-string" npm run db:studio

# View PRODUCTION database (be careful!)
POSTGRES_URL="your-prod-connection-string" npm run db:studio
```

### Database Verification

To verify your databases are properly separated:

1. **Create test data in each environment** to ensure isolation
2. **Check that data doesn't leak between environments**
3. **Verify each database has unique connection strings**

**Important Security Notes:**
- Never commit .env files to git
- Use environment variables in CI/CD pipelines
- Keep production credentials completely separate
- Each environment has its own isolated database

## 🚀 Usage

### Enabling YOLO Mode (Autonomous Remediation)

YOLO mode allows the agent to automatically execute remediation commands without human approval.

**Prerequisites:**
1. Working Kubernetes cluster
2. Valid `ANTHROPIC_API_KEY` in `.env`
3. Proper RBAC permissions for kubectl operations

**Quick Setup:**
```bash
cd backend
./enable_yolo_mode.sh  # Sets K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
```

**Manual Setup:**
1. Edit `backend/.env`:
   ```env
   K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
   K8S_ENABLED=true
   ```

2. Start the API server:
   ```bash
   uv run python api_server.py
   ```

3. In the frontend, set AI Mode to "YOLO" using the toggle

**How YOLO Mode Works:**
1. **Alert Received**: PagerDuty webhook triggers the agent
2. **Pattern Detection**: Agent tries to match alert to known patterns
3. **Generic Fallback**: If no pattern matches in YOLO mode, uses generic pod error resolution
4. **Action Generation**: Creates remediation actions with various confidence levels
5. **Auto-Execution**: In YOLO mode, ALL actions are executed regardless of confidence
6. **Command Execution**: Runs actual kubectl commands to fix issues:
   - Identifies error pods
   - Restarts crashed pods
   - Increases memory limits for OOM issues
   - Scales deployments if needed

**YOLO Mode Capabilities:**
- Always executes remediation if ANY resolution actions are found
- Ignores confidence threshold checks
- Handles generic pod errors when specific patterns don't match
- Executes commands like `kubectl patch deployment` to increase memory limits
- Automatically restarts failed pods
- Verifies fixes and auto-resolves PagerDuty incidents

### PagerDuty Integration

**Required Configuration:**
```env
PAGERDUTY_API_KEY=your-api-key-here
PAGERDUTY_USER_EMAIL=your-email@company.com
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
```

**Setup Steps:**
1. Generate API key from: PagerDuty → Configuration → API Access Keys
2. Ensure the user email is a valid user in your PagerDuty account
3. The user must have permissions to acknowledge and resolve incidents

**YOLO Mode Behavior:**
- Always attempts to acknowledge and resolve incidents
- Ignores PagerDuty API errors and continues execution
- Forces resolution even if some remediation actions fail
- Logs warnings about PagerDuty errors but treats incidents as resolved

**Troubleshooting:**
- **"Requester User Not Found"**: Email in `PAGERDUTY_USER_EMAIL` is not valid
- **API Key Issues**: Verify API key has full access permissions
- **Authentication Errors**: Check if API key is still valid and no extra spaces in .env

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
- `GET /alerts/{alert_id}` - Get alert details

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
   kubectl apply -f crash-loop-test.yaml
   ```

3. **Run the agent**:
   ```bash
   cd backend
   uv run python main.py
   ```

### Testing Kubernetes Failures

Use the included testing script to simulate real Kubernetes failures:

```bash
# Usage from project root
./fuck_kubernetes.sh [1-5|all|random|clean]

# Simulates:
# 1 - Pod crashes (CrashLoopBackOff)
# 2 - Image pull errors (ImagePullBackOff)  
# 3 - OOM kills
# 4 - Deployment failures
# 5 - Service unavailability

# The script:
# - Creates issues in 'fuck-kubernetes-test' namespace
# - Triggers CloudWatch alarms within 60 seconds
# - Sends alerts through SNS → PagerDuty → Slack
# - Helps verify the entire alerting pipeline
```

### Quick Database Testing

For rapid database testing:

```bash
# Step 1: Set up Neon projects (dreamops-local, dreamops-staging, dreamops-prod)
# Step 2: Create environment files with connection strings
# Step 3: Run tests

cd frontend
npm install postgres
node test-db-connections.mjs
```

Expected output:
```
🚀 DreamOps Database Connection Tests
=====================================

🔍 Testing LOCAL database...
   ✅ Connected successfully!
   📊 Database: oncall_agent
   👤 User: your_user

🔍 Testing STAGING database...
   ✅ Connected successfully!

🔍 Testing PRODUCTION database...
   ✅ Connected successfully!

🔒 Database Separation Check
============================
✅ Perfect! All 3 environments use different databases.
```

## 🚢 AWS Deployment

### Option 1: Terraform (Recommended)

**Full Infrastructure Deployment:**

1. **Configure AWS credentials**:
   ```bash
   aws configure
   ```

2. **Deploy infrastructure**:
   ```bash
   cd infrastructure/terraform
   terraform init
   terraform plan
   terraform apply
   ```

3. **Deploy applications**:
   ```bash
   # Backend deployment via GitHub Actions
   git push origin main
   
   # Frontend deployment to S3/CloudFront
   cd frontend
   npm run build
   aws s3 sync dist/ s3://your-bucket-name
   aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
   ```

### Option 2: AWS Amplify (Frontend Only)

**Quick AWS CLI Setup:**
```bash
# Create Amplify App
aws amplify create-app \
  --name "dreamops-frontend" \
  --repository "https://github.com/yourusername/oncall-agent" \
  --platform "WEB_COMPUTE" \
  --region ap-south-1

# Note the App ID from the output
APP_ID="your-app-id"

# Update app with build spec
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

aws amplify update-app \
  --app-id $APP_ID \
  --build-spec file://amplify.yml

# Create branch
aws amplify create-branch \
  --app-id $APP_ID \
  --branch-name main

# Set environment variables
aws amplify update-branch \
  --app-id $APP_ID \
  --branch-name main \
  --environment-variables \
    NEXT_PUBLIC_API_URL=https://your-api-url.com \
    POSTGRES_URL=postgresql://user:pass@host:5432/db
```

**Manual Console Setup:**
1. Go to AWS Amplify Console
2. Click "New app" → "Host web app"
3. Select "GitHub" and authorize
4. Select repository and branch
5. Configure as monorepo with `frontend` as app root
6. Set environment variables
7. Deploy

**Your app will be available at:** `https://main.YOUR_APP_ID.amplifyapp.com`

### Custom Domain Setup

**For Amplify:**
```bash
# Add custom domain
aws amplify create-domain-association \
  --app-id YOUR_APP_ID \
  --domain-name yourdomain.com \
  --sub-domain-settings prefix=app,branchName=main

# Get domain association status
aws amplify get-domain-association \
  --app-id YOUR_APP_ID \
  --domain-name yourdomain.com
```

**DNS Records to Add:**
1. **CNAME Record**: `app` → `<branch>.<app-id>.amplifyapp.com`
2. **Verification Record**: `_<verification-id>.app` → `_<verification-value>.acm-validations.aws`

### GitHub Secrets Required

Add these to your GitHub repository secrets:
- `AWS_ACCESS_KEY_ID` - AWS access key for deployment
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `CLOUDFRONT_DISTRIBUTION_ID` - CloudFront ID (after initial deployment)
- `AMPLIFY_APP_ID` - Your Amplify app ID
- `NEON_DATABASE_URL_STAGING` - Staging database connection string
- `NEON_DATABASE_URL_PROD` - Production database connection string

## 🔧 Technical Details

### JSON Serialization Fix

**Issue:** The API was returning `TypeError: Object of type ResolutionAction is not JSON serializable`

**Root Cause:** Execution context was storing entire `ResolutionAction` dataclass objects

**Fix Applied:**
```python
# Before (problematic)
execution_context = {
    "action": action,  # ResolutionAction dataclass
    ...
}

# After (fixed)
execution_context = {
    "action": {
        "action_type": action.action_type,
        "description": action.description,
        "params": action.params,
        "confidence": action.confidence,
        "risk_level": action.risk_level,
        "estimated_time": action.estimated_time,
        "rollback_possible": action.rollback_possible
    },
    ...
}
```

**Enhancement:** Added `to_dict()` method to `ResolutionAction` dataclass for consistent serialization.

### YOLO Mode Implementation

**Key fixes implemented:**
1. **Python Type Annotations**: Fixed `callable | None` syntax errors by using `Optional[Callable]`
2. **Agent Configuration Sync**: Modified to use `EnhancedOncallAgent` with current AI mode
3. **Alert Pattern Detection**: Added patterns for CloudWatch/metrics-based alerts
4. **Remediation Logic**: YOLO mode now ALWAYS executes if ANY resolution actions are found
5. **New Resolution Strategies**: Added generic pod error resolution and OOM kill handling

**YOLO Mode Capabilities:**
- `resolve_generic_pod_errors()`: Handles generic pod issues
- `resolve_oom_kills()`: Specific OOM remediation
- `_execute_identify_error_pods()`: Finds pods in error states
- `_execute_restart_error_pods()`: Deletes pods to force restart
- `_execute_increase_memory_limits()`: Patches deployments with higher memory

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check this README and the `CLAUDE.md` file for AI assistant instructions
- **Issues**: Report bugs and request features via GitHub Issues
- **Community**: Join our discussions in GitHub Discussions

## 🎯 Roadmap

- [ ] Slack integration for notifications
- [ ] Enhanced monitoring dashboard
- [ ] Multi-cluster Kubernetes support
- [ ] Advanced machine learning for pattern recognition
- [ ] Custom alert routing and escalation
- [ ] Integration with more monitoring tools (Datadog, New Relic, etc.)

---

*Dream easy knowing your infrastructure is monitored and maintained by AI. 🌙*