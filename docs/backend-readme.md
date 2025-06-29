# DreamOps - AI-Powered On-Call Agent

DreamOps is an autonomous incident response system that uses AI to automatically resolve infrastructure issues. The system integrates with PagerDuty, Kubernetes, GitHub, and other services to provide real-time incident detection, analysis, and resolution.

## Table of Contents

1. [Project Overview & Introduction](#project-overview--introduction)
2. [Quick Start Guide](#quick-start-guide)
3. [Architecture & Technical Details](#architecture--technical-details)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [Features & Integrations](#features--integrations)
7. [Payment System](#payment-system)
8. [Deployment](#deployment)
9. [Testing & Development](#testing--development)
10. [CI/CD](#cicd)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)
13. [Contributing](#contributing)

## Project Overview & Introduction

DreamOps is an intelligent AI-powered incident response and infrastructure management platform that provides:

### Core Features
- **Autonomous Incident Resolution**: AI-powered analysis and automated remediation using Claude AI
- **Multi-Platform Integration**: Kubernetes, PagerDuty, GitHub, Notion support via MCP (Model Context Protocol)
- **YOLO Mode**: Fully autonomous operations with safety mechanisms
- **Real-Time Dashboard**: Monitor incidents and agent actions in real-time with WebSocket integration
- **Complete Audit Trail**: Full logging and tracking of all operations
- **Free Tier with Payment Integration**: 3 free alerts per month with PhonePe payment gateway for upgrades

### Technology Stack
- **Claude API**: For intelligent incident analysis and decision making
- **MCP (Model Context Protocol)**: For integrating with external tools and services
- **FastAPI**: Web framework for the REST API and webhooks
- **Python AsyncIO**: For concurrent operations and real-time processing
- **uv**: Modern Python package manager for dependency management
- **Next.js**: Frontend SaaS interface with real-time dashboard
- **Terraform**: AWS infrastructure deployment and management
- **Neon**: PostgreSQL database with environment separation
- **Docker**: Containerization for consistent deployments
- **PhonePe**: Payment gateway integration for subscription management

## Quick Start Guide

### Prerequisites
- Node.js 18+ and Python 3.11+
- Docker and Docker Compose
- Kubernetes cluster (optional, for K8s features)
- Anthropic API key
- Neon PostgreSQL database accounts

### Quick Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/oncall-agent.git
   cd oncall-agent
   ```

2. **Set up the backend**:
   ```bash
   cd backend
   pip install uv
   uv sync
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Set up the frontend**:
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

4. **Start the services**:
   ```bash
   # Start backend
   cd backend && uv run python api_server.py

   # Start frontend (in another terminal)
   cd frontend && npm run dev
   ```

5. **Access the dashboard**: Open http://localhost:3000

### Testing Payment Flow
```bash
cd backend
python test_payment_upgrade.py
```

## Architecture & Technical Details

### Key Architecture Decisions

1. **Modular MCP Integrations**: All integrations extend `MCPIntegration` base class in `src/oncall_agent/mcp_integrations/base.py`
2. **Async-First**: All operations are async to handle concurrent MCP calls efficiently
3. **Configuration-Driven**: Uses pydantic for config validation and environment variables
4. **Type-Safe**: Extensive use of type hints throughout the codebase
5. **Retry Logic**: Built-in exponential backoff for network operations (configurable via MCP_MAX_RETRIES)
6. **Singleton Config**: Global configuration instance accessed via `get_config()`
7. **Environment Separation**: Complete database and configuration isolation between local/staging/production
8. **YOLO Mode**: Autonomous remediation mode that executes fixes without human approval

### Project Structure

```
backend/
├── src/oncall_agent/
│   ├── agent.py              # Core agent logic
│   ├── agent_enhanced.py     # Enhanced agent with YOLO mode
│   ├── agent_executor.py     # Command execution engine
│   ├── api/                  # API routers and schemas
│   │   ├── routers/
│   │   │   ├── agent.py
│   │   │   ├── incidents.py
│   │   │   ├── integrations.py
│   │   │   ├── alert_tracking.py
│   │   │   ├── payments.py
│   │   │   └── mock_payments.py
│   │   ├── schemas.py
│   │   ├── webhooks.py
│   │   └── auth.py
│   ├── config.py             # Configuration management
│   ├── mcp_integrations/     # MCP integration modules
│   │   ├── base.py          # Base integration class
│   │   ├── kubernetes.py    # Kubernetes integration
│   │   ├── kubernetes_enhanced.py
│   │   ├── github_mcp.py    # GitHub integration
│   │   ├── notion_direct.py # Notion integration
│   │   └── pagerduty.py     # PagerDuty integration
│   ├── services/            # Business logic services
│   │   ├── phonepe_service.py
│   │   └── phonepe_sdk_service.py
│   ├── strategies/          # Resolution strategies
│   │   ├── kubernetes_resolver.py
│   │   └── deterministic_k8s_resolver.py
│   └── utils/               # Utility functions
│       └── logger.py        # Logging configuration
├── tests/                    # All test files
├── examples/                 # Example scripts and demos
├── scripts/                  # Utility scripts
├── main.py                   # CLI entry point
├── api_server.py            # API server entry point
└── Dockerfile.prod          # Production Docker image

frontend/
├── app/                     # Next.js app router
│   ├── (dashboard)/        # Dashboard pages
│   │   ├── dashboard/
│   │   ├── incidents/
│   │   ├── integrations/
│   │   ├── alerts-test/
│   │   └── pricing/
│   ├── (login)/            # Authentication pages
│   ├── payment/            # Payment flow pages
│   └── api/                # API routes
├── components/             # React components
│   ├── ui/                # UI components
│   ├── incidents/         # Incident-specific components
│   ├── dashboard/         # Dashboard components
│   └── payments/          # Payment components
├── lib/                   # Utilities and configurations
│   ├── db/               # Database utilities
│   ├── auth/             # Authentication
│   └── hooks/            # React hooks
└── scripts/              # Build and deployment scripts
```

### Data Flow

```
PagerDuty Alert → Webhook → AI Analysis → MCP Integration → K8s Execution → Verification → Resolution
```

### Core Components

1. **AI Agent**: Claude-powered incident analysis and resolution
2. **MCP Integrations**: Pluggable external service connections
3. **Execution Engine**: Secure command execution with rollback capabilities
4. **Database Layer**: PostgreSQL with Drizzle ORM for persistence
5. **API Layer**: FastAPI backend with real-time WebSocket support
6. **Frontend**: Next.js dashboard with real-time incident monitoring
7. **Payment System**: PhonePe integration with free tier and subscription management

## Installation & Setup

### Detailed Installation Steps

#### 1. Environment Setup

**Backend Setup**:
```bash
cd backend
pip install uv  # Install UV package manager
uv sync        # Install dependencies
cp .env.example .env
```

**Frontend Setup**:
```bash
cd frontend
npm install    # or pnpm install
cp .env.example .env.local
```

#### 2. Database Setup

DreamOps uses separate Neon PostgreSQL databases for different environments:

1. **Create Neon Projects**:
   - Go to [neon.tech](https://neon.tech)
   - Create 3 separate projects:
     - `dreamops-local` - For local development
     - `dreamops-staging` - For staging/testing
     - `dreamops-prod` - For production

2. **Configure Database Connections**:
   
   Backend `.env.local`:
   ```env
   DATABASE_URL=postgresql://[your-local-neon-connection-string]
   ENVIRONMENT=local
   ```
   
   Frontend `.env.local`:
   ```env
   POSTGRES_URL=postgresql://[your-local-neon-connection-string]
   NEXT_PUBLIC_ENVIRONMENT=local
   ```

3. **Run Migrations**:
   ```bash
   cd frontend
   npm run db:migrate:local      # Local
   npm run db:migrate:staging    # Staging
   npm run db:migrate:production # Production (requires confirmation)
   ```

4. **Test Connections**:
   ```bash
   cd frontend
   npm run test:db  # Tests all database connections
   ```

#### 3. Service Configuration

Configure all required services in your environment files:

**Backend Configuration** (`backend/.env`):
```env
# Core Configuration
ANTHROPIC_API_KEY=your-anthropic-key
DATABASE_URL=postgresql://...
LOG_LEVEL=DEBUG
ENVIRONMENT=local

# Kubernetes Integration
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false

# PagerDuty Integration
PAGERDUTY_API_KEY=your-pagerduty-key
PAGERDUTY_USER_EMAIL=your-email@company.com
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret

# GitHub Integration
GITHUB_TOKEN=your-github-token
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo

# PhonePe Payment Gateway
PHONEPE_MERCHANT_ID=MERCHANTUAT
PHONEPE_SALT_KEY=099eb0cd-02cf-4e2a-8aca-3e6c6aff0399
PHONEPE_SALT_INDEX=1
PHONEPE_BASE_URL=https://api-preprod.phonepe.com/apis/pg-sandbox
PHONEPE_REDIRECT_URL=http://localhost:3000/payment/redirect
PHONEPE_CALLBACK_URL=http://localhost:8000/api/v1/payments/callback
```

**Frontend Configuration** (`frontend/.env.local`):
```env
# Database
POSTGRES_URL=postgresql://...

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=local

# Payment Configuration
NEXT_PUBLIC_USE_MOCK_PAYMENTS=true  # Set to false for real PhonePe
```

## Configuration

### Environment Files Overview

The project uses environment-based configuration for different deployment scenarios:

#### Development Environment
- Mock payments enabled by default
- Debug logging enabled
- Local database connections
- Destructive operations disabled

#### Staging Environment
- PhonePe UAT environment
- Test credentials
- Staging database
- Limited destructive operations

#### Production Environment
- PhonePe production environment
- Live credentials
- Production database
- Full YOLO mode capabilities (when enabled)

### Service-Specific Configuration

#### Kubernetes Configuration
```env
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false  # Set to true for YOLO mode
```

#### PagerDuty Configuration
```env
PAGERDUTY_API_KEY=your-api-key-here
PAGERDUTY_USER_EMAIL=your-email@company.com  # Must be valid PagerDuty user
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
```

#### Payment Configuration
```env
# For Mock Payments (Development)
NEXT_PUBLIC_USE_MOCK_PAYMENTS=true

# For Real PhonePe (Production)
NEXT_PUBLIC_USE_MOCK_PAYMENTS=false
PHONEPE_MERCHANT_ID=YOUR_ACTUAL_MERCHANT_ID
PHONEPE_SALT_KEY=YOUR_ACTUAL_SALT_KEY
PHONEPE_BASE_URL=https://api.phonepe.com/apis/hermes
```

## Features & Integrations

### Core Features

#### AI-Powered Incident Resolution
- Analyzes PagerDuty alerts and determines remediation actions
- Supports pattern recognition for common infrastructure issues
- Provides confidence scores and risk assessments for all actions
- Uses Claude AI for intelligent decision making

#### YOLO Mode (Autonomous Operations)
YOLO Mode enables fully autonomous incident resolution:

**Configuration**:
```bash
cd backend
./enable_yolo_mode.sh  # Sets K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
```

**Capabilities**:
- Automatically executes fixes without human approval
- Pattern-based resolution strategies
- Built-in safety mechanisms and rollback capabilities
- Generic fallback for unknown patterns

**Supported Actions**:
- Pod management (restart, delete, scale)
- Resource adjustments (memory, CPU limits)
- Deployment operations (rollback, restart)
- Service troubleshooting

#### Multi-Platform Integrations

##### Kubernetes Integration
The Kubernetes integration provides comprehensive cluster management:

**Features**:
- Pod management (list, logs, describe, restart)
- Deployment operations (status, scale, rollback)
- Service monitoring
- Event retrieval
- Automated resolution strategies
- Memory limit adjustments
- Resource constraint analysis

**Enhanced Kubernetes Integration**:
- Auto-discovery of K8s contexts
- Multi-context support
- Connection testing
- RBAC permission verification
- Cluster information retrieval
- No MCP server dependency

**Configuration UI**:
Access at `/integrations/kubernetes` for:
- Context discovery
- Saved configurations management
- Cluster details viewing
- One-click testing

##### GitHub Integration
**Capabilities**:
- Issue management (create, update, close)
- Pull request automation
- Repository monitoring
- Code analysis

**Example Operations**:
```python
# Create incident issue
await github.execute_action("create_issue", {
    "title": "Production Incident: API Gateway Down",
    "body": "Automated incident report from DreamOps AI agent",
    "labels": ["incident", "production", "urgent"]
})
```

##### PagerDuty Integration
**Features**:
- Automatic incident acknowledgment
- Incident resolution with details
- Progress note addition
- Escalation management

**Webhook Events**:
- `incident.trigger`: New incident created
- `incident.acknowledge`: Incident acknowledged
- `incident.resolve`: Incident resolved
- `incident.escalate`: Incident escalated

##### Notion Integration
**Capabilities**:
- Incident documentation
- Knowledge base management
- Runbook access
- Metrics tracking

### Real-Time Monitoring
- Live dashboard showing active incidents and agent actions
- WebSocket-based real-time updates
- Complete audit trail with detailed logging
- Alert usage tracking and limits

## Payment System

### Overview
DreamOps includes a comprehensive payment system with:
- **Free Tier**: 3 alerts per month
- **Paid Tiers**: Starter, Pro, and Enterprise plans
- **PhonePe Integration**: Secure payment processing
- **Mock Payment Mode**: For testing and development

### Alert Tracking & Limits

#### Free Tier Limits
- Every new team gets 3 free alerts per month
- Alert usage is tracked automatically
- After 3 alerts, the system blocks further processing
- Users are prompted to upgrade their plan

#### Subscription Plans
1. **Starter**: ₹999/month - 50 alerts
2. **Pro**: ₹2,999/month - 200 alerts (Recommended)
3. **Enterprise**: ₹9,999/month - Unlimited alerts

### Payment Flow

1. **User Exhausts Free Alerts**
   - Alert usage card shows: 3/3 (100% used)
   - "Upgrade Plan" button appears
   - Next alert creation is blocked

2. **User Clicks Upgrade Plan**
   - Upgrade modal shows 3 plans
   - User selects desired plan

3. **Payment Processing**
   - Mock Mode: Instant simulation
   - Real Mode: PhonePe redirect

4. **Account Upgrade**
   - Alert limit increased
   - Account tier badge updated
   - Can create alerts again

### PhonePe Integration

#### Test Environment Setup
```env
PHONEPE_MERCHANT_ID=MERCHANTUAT
PHONEPE_SALT_KEY=099eb0cd-02cf-4e2a-8aca-3e6c6aff0399
PHONEPE_SALT_INDEX=1
PHONEPE_ENV=UAT
```

#### Production Setup
1. Register at [business.phonepe.com](https://business.phonepe.com)
2. Complete KYC verification
3. Get production credentials
4. Update environment variables

#### Test Credentials
**For Successful Payment**:
- UPI: `success@paytm`
- Card: `4242 4242 4242 4242`
- CVV: `123`
- OTP: `123456`

**For Failed Payment**:
- UPI: `failure@paytm`
- Card: `5555 5555 5555 4444`

### Payment API Endpoints
- `POST /api/v1/payments/initiate` - Start payment
- `POST /api/v1/payments/callback` - PhonePe callback
- `GET /api/v1/payments/redirect` - User redirect
- `POST /api/v1/payments/status` - Check status
- `GET /api/v1/payments/plans` - Get plans

### Testing Payment System
```bash
# Run the test script
cd backend
python test_payment_upgrade.py

# Or test via API
curl -X POST http://localhost:8000/api/v1/mock-payments/initiate \
  -H "Content-Type: application/json" \
  -d '{"team_id": "team_123", "amount": 299900, "plan": "PRO"}'
```

## Deployment

### Deployment Options

DreamOps supports multiple deployment strategies:

#### Option 1: Terraform Infrastructure (Recommended)

**Full Infrastructure Deployment**:
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

**Infrastructure Components**:
- VPC with public/private subnets across 2 AZs
- ECS Fargate cluster for the backend
- Application Load Balancer for backend API
- S3 + CloudFront for frontend hosting
- ECR for Docker image storage
- CloudWatch for monitoring and alarms
- Secrets Manager for sensitive configuration

#### Option 2: AWS Amplify (Frontend Only)

**Quick Setup**:
```bash
# Create Amplify App
aws amplify create-app \
  --name "dreamops-frontend" \
  --repository "https://github.com/yourusername/oncall-agent" \
  --platform "WEB_COMPUTE" \
  --region ap-south-1

# Configure build settings
aws amplify update-app \
  --app-id $APP_ID \
  --build-spec file://amplify.yml

# Set environment variables
aws amplify update-branch \
  --app-id $APP_ID \
  --branch-name main \
  --environment-variables \
    NEXT_PUBLIC_API_URL=https://your-api-url.com \
    POSTGRES_URL=postgresql://...
```

**Build Configuration** (`amplify.yml`):
```yaml
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - npm install -g pnpm
            - pnpm install
        build:
          commands:
            - pnpm run build
      artifacts:
        baseDirectory: .next
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
    appRoot: frontend
```

#### Option 3: Docker Deployment

**Development**:
```bash
docker-compose up
```

**Production**:
```bash
# Build production image
docker build -t oncall-agent -f backend/Dockerfile.prod backend/

# Run with environment variables
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your-key \
  -e DATABASE_URL=your-db-url \
  oncall-agent
```

### Environment-Specific Deployments

#### Staging Deployment
```bash
export NODE_ENV=staging
export DATABASE_URL=$NEON_DATABASE_URL_STAGING

cd frontend
npm run build:staging
npm run deploy:staging
```

#### Production Deployment
```bash
export NODE_ENV=production
export DATABASE_URL=$NEON_DATABASE_URL_PROD

cd frontend
npm run build:production
npm run deploy:production  # Requires approval
```

### Custom Domain Setup

#### For Amplify
```bash
# Add custom domain
aws amplify create-domain-association \
  --app-id YOUR_APP_ID \
  --domain-name yourdomain.com \
  --sub-domain-settings prefix=app,branchName=main
```

#### DNS Configuration
Add these DNS records:
1. **CNAME Record**: `app` → `<branch>.<app-id>.amplifyapp.com`
2. **Verification Record**: As provided by AWS

### Monitoring and Logging

#### CloudWatch Integration
- Application logs sent to CloudWatch
- Custom metrics for response times and error rates
- Automated alerting for critical issues
- Real-time monitoring dashboards

#### Log Analysis
```bash
# View application logs
aws logs tail /ecs/dreamops-backend --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /ecs/dreamops-backend \
  --filter-pattern "ERROR"
```

## Testing & Development

### Development Workflow

#### Development Commands
- **Install dependencies**: `uv sync`
- **Run the agent**: `uv run python main.py`
- **Run API server**: `uv run python api_server.py`
- **Add dependency**: `uv add <package>`
- **Add dev dependency**: `uv add --dev <package>`

#### Database Operations
```bash
cd frontend
npm run db:migrate:local      # Migrate local database
npm run db:migrate:staging    # Migrate staging database
npm run db:migrate:production # Migrate production (requires confirmation)
npm run db:studio            # Open Drizzle Studio
npm run test:db             # Test all database connections
```

### Testing Approach

#### Pre-commit Checklist
**ALWAYS run these commands before finishing any task**:
```bash
# 1. Run linter and fix any issues
uv run ruff check . --fix

# 2. Run type checker
uv run mypy . --ignore-missing-imports

# 3. Run all tests
uv run pytest tests/

# 4. Verify the application still runs
uv run python main.py

# 5. Test API server
uv run python api_server.py
```

#### Testing Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Cross-component interactions
3. **E2E Tests**: Complete workflow validation
4. **Load Tests**: Performance and scalability testing

#### Kubernetes Testing
The project includes `fuck_kubernetes.sh` for simulating failures:

```bash
# Usage from project root
./fuck_kubernetes.sh [1-5|all|random|clean]

# Simulates:
# 1 - Pod crashes (CrashLoopBackOff)
# 2 - Image pull errors (ImagePullBackOff)  
# 3 - OOM kills
# 4 - Deployment failures
# 5 - Service unavailability
```

#### Payment Testing
```bash
# Test payment flow
cd backend
python test_payment_upgrade.py

# Test alert flow
python test_alert_flow.py

# Manual API testing
curl -X POST http://localhost:8000/api/v1/alerts/ \
  -H "Content-Type: application/json" \
  -d '{"team_id":"team_123","incident_id":"test_1","title":"Test Alert"}'
```

### YOLO Mode Testing

#### Test Scenarios
1. **Pod Crash Test**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: crash-test
   spec:
     replicas: 1
     template:
       spec:
         containers:
         - name: crasher
           image: busybox
           command: ["sh", "-c", "exit 1"]
   ```

2. **OOM Test**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: oom-test
   spec:
     replicas: 1
     template:
       spec:
         containers:
         - name: memory-hog
           image: progrium/stress
           resources:
             limits:
               memory: "100Mi"
           command: ["stress", "--vm", "1", "--vm-bytes", "200M"]
   ```

## CI/CD

### GitHub Actions Workflows

The CI/CD pipeline includes several specialized workflows:

#### Workflow Structure
```
.github/workflows/
├── check-markdown-files.yml     # Documentation governance
├── backend-ci.yml               # Backend testing and deployment
├── frontend-ci.yml              # Frontend testing and deployment
├── security-scan.yml            # Security vulnerability scanning
└── integration-tests.yml        # Cross-service integration tests
```

#### Documentation Governance
The `check-markdown-files.yml` workflow enforces documentation organization:
- Only permits `.md` files in specific locations
- Encourages use of the `/docs` folder
- Prevents documentation sprawl

**Allowed Locations**:
- `./README.md` - Main project documentation
- `./CLAUDE.md` - AI assistant instructions
- `./docs/*.md` - Organized documentation files

#### Backend CI/CD Pipeline
**Testing Phase**:
- Python 3.11 setup
- Dependency installation with uv
- Unit tests with pytest
- Linting with ruff
- Type checking with mypy

**Security Scanning**:
- Bandit security scan
- Dependency vulnerability checks
- SAST analysis

**Deployment**:
- Docker build and push to ECR
- ECS service update
- Health check verification

#### Frontend CI/CD Pipeline
**Build and Test**:
- Node.js 18 setup
- Dependency installation
- Type checking
- Unit tests
- Production build

**Database Migration**:
- Environment-specific migrations
- Automated for staging
- Manual approval for production

**Deployment Options**:
- AWS Amplify deployment
- S3 + CloudFront deployment

### GitHub Secrets Required

#### AWS Secrets
- `AWS_ACCESS_KEY_ID` - AWS access key for deployment
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `ECR_REGISTRY` - ECR registry URL
- `S3_BUCKET` - S3 bucket for frontend deployment
- `CLOUDFRONT_DISTRIBUTION_ID` - CloudFront distribution ID

#### Database Secrets
- `POSTGRES_URL_STAGING` - Staging database connection string
- `POSTGRES_URL_PROD` - Production database connection string

#### API Keys
- `ANTHROPIC_API_KEY` - Anthropic API key
- `PAGERDUTY_API_KEY` - PagerDuty API key
- `AMPLIFY_APP_ID` - AWS Amplify app ID

### Security Scanning

#### Vulnerability Scanning
```yaml
dependency-scan:
  runs-on: ubuntu-latest
  steps:
    - name: Backend dependency check
      run: |
        cd backend
        pip install safety
        safety check
    
    - name: Frontend dependency check
      run: |
        cd frontend
        npm audit --audit-level high
```

#### Secret Scanning
- GitHub automatically scans for exposed secrets
- Additional scanning with TruffleHog
- Regular security audits

### Deployment Strategies

#### Blue-Green Deployment
- Deploy new version to green environment
- Health check green environment
- Switch traffic to green
- Cleanup blue environment

#### Rollback Procedures
```bash
# ECS Rollback
aws ecs update-service \
  --cluster dreamops-cluster \
  --service dreamops-backend \
  --task-definition dreamops-backend:PREVIOUS_REVISION

# Amplify Rollback
aws amplify start-job \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --job-type RELEASE \
  --job-id PREVIOUS_JOB_ID
```

## Troubleshooting

### Common Issues & Solutions

#### JSON Serialization Errors
**Problem**: `TypeError: Object of type ResolutionAction is not JSON serializable`

**Solution**: Always convert dataclasses to dictionaries:
```python
# Add to_dict() method to dataclasses
def to_dict(self) -> dict[str, Any]:
    return asdict(self)

# Use in execution context
execution_context = {
    "action": action.to_dict(),
    "result": result
}
```

#### PagerDuty API Errors
**Problem**: "Requester User Not Found"

**Solution**: 
1. Log into PagerDuty
2. Go to "My Profile" 
3. Copy your exact email address
4. Update `PAGERDUTY_USER_EMAIL` in your `.env` file

#### Database Connection Issues
**Problem**: Connection timeouts or SSL errors

**Solution**: 
1. Verify connection strings include `?sslmode=require`
2. Check Neon project is active (not suspended)
3. Ensure no `&channel_binding=require` in connection string

#### YOLO Mode Not Executing
**Problem**: Agent not executing remediation actions

**Solution**:
1. Verify `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`
2. Check `K8S_ENABLED=true`
3. Ensure kubectl is configured and working
4. Verify API server is running with correct configuration

#### Frontend Build Issues
**Problem**: Next.js build failures

**Solution**:
1. Check all environment variables are set
2. Verify database connection strings
3. Ensure API URL is accessible
4. Check for TypeScript errors

#### Payment Integration Issues
**Problem**: Payment not working or alert limit not updating

**Solution**:
1. Check PhonePe credentials in backend .env
2. Try mock payments first (simpler)
3. Verify callback URL is accessible
4. Check backend logs for errors
5. Ensure team_id matches (default: "team_123")

### Debug Commands

```bash
# Test Kubernetes connectivity
kubectl cluster-info

# Check RBAC permissions
kubectl auth can-i create pods
kubectl auth can-i patch deployments

# Test PagerDuty API
curl -H "Authorization: Token token=YOUR_API_KEY" \
     https://api.pagerduty.com/users

# Check alert usage
curl http://localhost:8000/api/v1/alert-tracking/usage/team_123

# Test database connections
cd frontend && npm run test:db

# View YOLO mode actions
grep -A 10 -B 10 "YOLO MODE" /var/log/dreamops/agent.log
```

## API Reference

### REST API Endpoints

#### Health & Status
- `GET /health` - Health check endpoint

#### Alerts
- `POST /api/v1/alerts` - Submit new alerts for processing
- `GET /api/v1/alerts/{alert_id}` - Get alert details
- `POST /api/v1/alerts/reset-usage/{team_id}` - Reset alert usage (dev only)

#### Alert Tracking
- `GET /api/v1/alert-tracking/usage/{team_id}` - Get current usage
- `POST /api/v1/alert-tracking/record` - Record new alert
- `POST /api/v1/alert-tracking/upgrade` - Upgrade subscription
- `GET /api/v1/alert-tracking/plans` - Get available plans

#### Integrations
- `GET /api/v1/integrations` - List available MCP integrations
- `POST /api/v1/integrations/{name}/health` - Check specific integration health

#### Kubernetes Integration
- `GET /api/v1/integrations/kubernetes/discover` - Discover contexts
- `POST /api/v1/integrations/kubernetes/test` - Test connection
- `GET /api/v1/integrations/kubernetes/configs` - List configurations
- `POST /api/v1/integrations/kubernetes/configs` - Save configuration
- `GET /api/v1/integrations/kubernetes/cluster-info` - Get cluster details

#### Payments
- `POST /api/v1/payments/initiate` - Start payment
- `POST /api/v1/payments/callback` - PhonePe callback handler
- `GET /api/v1/payments/redirect` - Payment redirect handler
- `POST /api/v1/payments/status` - Check payment status
- `GET /api/v1/payments/plans` - Get subscription plans

#### Mock Payments (Development)
- `POST /api/v1/mock-payments/initiate` - Start mock payment
- `POST /api/v1/mock-payments/status` - Check mock payment status

#### Webhooks
- `POST /webhook/pagerduty` - PagerDuty webhook handler

#### Agent Configuration
- `GET /api/v1/agent/config` - Get current agent configuration
- `POST /api/v1/agent/config` - Update agent configuration

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### WebSocket Events
The frontend connects to the backend via WebSocket for real-time updates:
- `incident.new` - New incident created
- `incident.update` - Incident status updated
- `action.executed` - Agent action executed
- `alert.recorded` - New alert recorded

## Contributing

### Development Guidelines

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests for new functionality**
5. **Run the test suite**
6. **Submit a pull request**

### Code Style Guidelines
- Use descriptive variable names
- Add type hints to all functions
- Include docstrings for all public methods
- Follow PEP 8 conventions
- Use `async/await` for all I/O operations
- Handle exceptions gracefully with proper logging
- Use dataclasses for structured data
- Implement proper JSON serialization for API responses

### Adding New MCP Integrations

1. **Create file in** `src/oncall_agent/mcp_integrations/`
2. **Extend** `MCPIntegration` base class
3. **Implement all abstract methods**:
   ```python
   async def connect() -> bool
   async def disconnect() -> None
   async def fetch_context(params: Dict[str, Any]) -> Dict[str, Any]
   async def execute_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]
   def get_capabilities() -> List[str]
   async def health_check() -> bool
   ```
4. **Add configuration to** `.env.example`
5. **Update README with usage instructions**
6. **Add integration tests**

### Best Practices for AI Assistants

When working with this codebase:

1. **Always check the latest README.md and CLAUDE.md** for current instructions
2. **Test all changes locally** before suggesting them
3. **Consider environment separation** when making database changes
4. **Respect YOLO mode safety mechanisms** when adding new features
5. **Follow the established patterns** for error handling and logging
6. **Document any new integrations or features** thoroughly
7. **Test with multiple scenarios** including edge cases
8. **Ensure JSON serialization compatibility** for all API responses

### Code Review Checklist

Before submitting any changes:
- [ ] All tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Application runs successfully
- [ ] API endpoints respond correctly
- [ ] Database migrations work
- [ ] Documentation is updated
- [ ] Environment variables are documented
- [ ] Security considerations are addressed

## Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use different secrets for each environment
- Rotate API keys regularly
- Use least-privilege access for service accounts

### Database Security
- Each environment uses completely separate databases
- Connection strings include SSL requirements
- Database users have minimal required permissions
- Regular security updates for database instances

### Kubernetes Security
- RBAC permissions are minimally scoped
- Destructive operations require explicit enablement
- All kubectl commands are logged
- Namespace isolation for testing

### API Security
- Authentication required for sensitive endpoints
- Request validation using Pydantic models
- Rate limiting implemented
- Comprehensive audit logging

### Payment Security
- Use environment variables for PhonePe credentials
- Never log sensitive payment data
- Implement webhook signature verification
- Use HTTPS for all payment callbacks

## Performance Optimization

### Async Operations
- All I/O operations use async/await
- Concurrent processing of multiple alerts
- Connection pooling for database operations
- Efficient resource cleanup

### Caching Strategy
- Configuration cached in memory
- Database query results cached where appropriate
- Static assets served from CDN
- Browser caching for frontend resources

### Monitoring and Alerting
- CloudWatch integration for metrics
- Custom dashboards for system health
- Alerting on error rates and performance
- Real-time log streaming

## Support

For issues and questions:
1. Check the documentation
2. Review existing GitHub issues
3. Create a new issue with detailed information
4. Include logs and configuration details

### Important Files to Understand
1. **`src/oncall_agent/agent_enhanced.py`**: Enhanced agent with YOLO mode capabilities
2. **`src/oncall_agent/agent_executor.py`**: Command execution engine for Kubernetes operations
3. **`src/oncall_agent/mcp_integrations/base.py`**: Base class defining the MCP interface
4. **`src/oncall_agent/config.py`**: Configuration schema and defaults
5. **`src/oncall_agent/api/routers/`**: API endpoint implementations
6. **`main.py`**: Entry point showing how to use the agent
7. **`src/oncall_agent/strategies/deterministic_k8s_resolver.py`**: Kubernetes resolution strategies

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Anthropic for Claude AI capabilities
- The open-source community for the excellent tools and libraries
- Contributors who help improve DreamOps

---

## AI Assistant Instructions

This section provides comprehensive instructions for AI assistants (like Claude, GPT-4, etc.) on how to effectively work with this codebase.

### Important Notes
- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested

### Documentation Structure
Before making any changes, read the relevant documentation in the `/docs` folder:
- `docs/database-setup.md` - Database configuration for all environments
- `docs/pagerduty-integration.md` - PagerDuty setup and webhook configuration  
- `docs/yolo-mode.md` - Autonomous operation mode and safety mechanisms
- `docs/deployment.md` - AWS deployment options (Terraform, Amplify)
- `docs/mcp-integrations.md` - External service integrations and API usage
- `docs/technical-details.md` - Architecture, implementation details, and fixes
- `docs/ci-cd.md` - GitHub Actions workflows and deployment automation

Always check these documentation files for the latest information before implementing changes.