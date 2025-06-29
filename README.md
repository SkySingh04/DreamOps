# DreamOps - AI-Powered Incident Response Platform

> Dream easy while AI takes your on-call duty - Intelligent incident response and infrastructure management powered by Claude AI

## Table of Contents

- [Project Overview](#project-overview)
- [Quick Start Guide](#quick-start-guide)
- [Architecture & Technical Details](#architecture--technical-details)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
  - [PagerDuty Integration](#pagerduty-integration)
  - [Kubernetes Integration](#kubernetes-integration)
  - [PhonePe Payment Integration](#phonepe-payment-integration)
  - [Environment Separation](#environment-separation)
- [Features & Integrations](#features--integrations)
- [Payment System](#payment-system)
- [Deployment](#deployment)
  - [Docker Setup](#docker-setup)
  - [AWS Deployment](#aws-deployment)
- [Testing & Development](#testing--development)
- [CI/CD](#ci-cd)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## Project Overview

DreamOps is an intelligent AI-powered incident response and infrastructure management platform that automates on-call duties using Claude AI and Model Context Protocol (MCP) integrations.

### Key Features

- 🤖 **AI-Powered Incident Response**: Automatic alert analysis and remediation using Claude AI
- 🔧 **YOLO Mode**: Autonomous operation that executes fixes without human approval
- 🎯 **Smart Alert Routing**: Intelligent alert categorization and prioritization
- 🔌 **MCP Integrations**: Kubernetes, GitHub, PagerDuty, Notion, and Grafana
- 💳 **Flexible Payment System**: PhonePe integration with free tier (3 alerts/month)
- 📊 **Real-time Dashboard**: Next.js frontend with live incident tracking
- 🚀 **Cloud-Native**: Docker, Terraform, and AWS deployment ready
- 🔒 **Enterprise Security**: Complete environment separation and secure secrets management

### Technology Stack

- **Backend**: FastAPI, Python AsyncIO, uv package manager
- **Frontend**: Next.js 15, TypeScript, TailwindCSS, Drizzle ORM
- **AI**: Claude 3.5 Sonnet API, Model Context Protocol (MCP)
- **Database**: Neon PostgreSQL with environment separation
- **Infrastructure**: Docker, Terraform, AWS (ECS Fargate, S3, CloudFront)
- **Payments**: PhonePe Payment Gateway SDK
- **Monitoring**: CloudWatch, custom metrics and dashboards

## Quick Start Guide

### Prerequisites

#### For Docker Setup (Recommended):
- Docker and Docker Compose
- Anthropic API key for Claude

#### For Manual Setup:
- Python 3.12+
- Node.js 18+
- PostgreSQL database (we use Neon)
- Anthropic API key for Claude

### Fast Setup

#### Option 1: Docker Compose (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/oncall-agent.git
cd oncall-agent

# Start all services with Docker
./docker-dev.sh up

# Access the application:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

#### Option 2: Manual Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/oncall-agent.git
cd oncall-agent

# Backend setup
cd backend
pip install uv
uv sync
cp .env.example .env.local
# Edit .env.local with your API keys

# Frontend setup
cd ../frontend
npm install
cp .env.example .env.local
# Edit .env.local with your database URL

# Run with mock payments (development)
cd ..
./start-dev-with-mock-payments.sh
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Architecture & Technical Details

### System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   Next.js       │────▶│  FastAPI         │────▶│  Claude AI      │
│   Frontend      │     │  Backend         │     │  (Anthropic)    │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                         │
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  Neon           │     │  MCP             │     │  Alert          │
│  PostgreSQL     │     │  Integrations    │     │  Processing     │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Key Architecture Decisions

1. **Modular MCP Integrations**: All integrations extend `MCPIntegration` base class
2. **Async-First**: All operations use async/await for concurrent processing
3. **Configuration-Driven**: Pydantic for validation and environment variables
4. **Type-Safe**: Extensive TypeScript and Python type hints
5. **Retry Logic**: Built-in exponential backoff for network operations
6. **Environment Separation**: Complete isolation between local/staging/production
7. **YOLO Mode**: Autonomous remediation with safety mechanisms

### Project Structure

```
oncall-agent/
├── backend/
│   ├── src/oncall_agent/
│   │   ├── agent.py              # Core agent logic
│   │   ├── agent_enhanced.py     # Enhanced agent with YOLO mode
│   │   ├── agent_executor.py     # Command execution engine
│   │   ├── api/                  # FastAPI routes and schemas
│   │   ├── mcp_integrations/     # MCP integration modules
│   │   ├── services/             # Business logic services
│   │   └── strategies/           # Resolution strategies
│   ├── tests/                    # Test files
│   └── Dockerfile               # Production Docker image
├── frontend/
│   ├── app/                     # Next.js app router
│   ├── components/              # React components
│   ├── lib/                     # Utilities and database
│   └── scripts/                 # Build and deployment scripts
├── terraform/                   # Infrastructure as Code
└── docs/                       # Documentation
```

## Installation & Setup

### Backend Setup

1. **Install Dependencies**:
```bash
cd backend
pip install uv
uv sync
```

2. **Configure Environment**:
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
# Core Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
ENVIRONMENT=local
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# PagerDuty Integration
PAGERDUTY_ENABLED=true
PAGERDUTY_API_KEY=your-pagerduty-api-key
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret

# Kubernetes Integration
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false

# Payment Settings
USE_MOCK_PAYMENTS=true  # For development
PHONEPE_MERCHANT_ID=MERCHANTUAT
PHONEPE_SALT_KEY=099eb0cd-02cf-4e2a-8aca-3e6c6aff0399
```

3. **Run the Backend**:
```bash
uv run python api_server.py
```

### Frontend Setup

1. **Install Dependencies**:
```bash
cd frontend
npm install
```

2. **Configure Environment**:
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
# Database Configuration
POSTGRES_URL=postgresql://user:pass@host/dbname?sslmode=require

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
AUTH_SECRET=development-secret-key

# Payment Configuration
NEXT_PUBLIC_USE_MOCK_PAYMENTS=true
```

3. **Run Database Migrations**:
```bash
npm run db:migrate:local
```

4. **Run the Frontend**:
```bash
npm run dev
```

### Database Setup

The project uses Neon PostgreSQL with complete environment separation:

1. **Create Neon Projects**:
   - Create separate projects for local, staging, and production
   - Each environment has its own database instance

2. **Configure Connection Strings**:
   ```env
   # Local (.env.local)
   POSTGRES_URL=postgresql://neondb_owner:xxx@ep-xxx.region.neon.tech/neondb?sslmode=require
   
   # Staging (.env.staging)
   POSTGRES_URL=postgresql://neondb_owner:xxx@ep-yyy.region.neon.tech/neondb?sslmode=require
   
   # Production (.env.production)
   POSTGRES_URL=postgresql://neondb_owner:xxx@ep-zzz.region.neon.tech/neondb?sslmode=require
   ```

3. **Run Migrations**:
   ```bash
   # Local
   npm run db:migrate:local
   
   # Staging
   npm run db:migrate:staging
   
   # Production (requires confirmation)
   npm run db:migrate:production
   ```

## Configuration

### PagerDuty Integration

1. **Create Integration in PagerDuty**:
   - Go to Services → Service Directory
   - Select your service → Integrations tab
   - Add Integration → Search "Webhooks V3"
   - Copy the Integration Key

2. **Configure Webhook**:
   ```json
   {
     "webhook_url": "https://your-domain.com/webhook/pagerduty",
     "description": "Oncall Agent Webhook",
     "events": [
       "incident.triggered",
       "incident.acknowledged",
       "incident.resolved"
     ],
     "headers": {
       "X-Webhook-Secret": "your-secret-here"
     }
   }
   ```

3. **Environment Variables**:
   ```env
   PAGERDUTY_ENABLED=true
   PAGERDUTY_API_KEY=your-api-key
   PAGERDUTY_USER_EMAIL=your-email@company.com
   PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
   ```

### Kubernetes Integration

The Kubernetes integration provides comprehensive cluster management:

```env
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=your-context-name
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false  # Set true for YOLO mode
```

#### Available Actions
- Pod management (list, logs, describe, restart)
- Deployment operations (status, scale, rollback)
- Service monitoring and health checks
- Event retrieval and analysis
- Automated resolution strategies
- Resource constraint analysis

#### YOLO Mode Operations
When `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`:
- Automatic pod restarts for failures
- Memory limit adjustments for OOM issues
- Deployment scaling and patches
- Configuration updates

### Payment System Configuration

#### PhonePe Integration

1. **Test Credentials** (UAT):
   ```env
   PHONEPE_MERCHANT_ID=MERCHANTUAT
   PHONEPE_SALT_KEY=099eb0cd-02cf-4e2a-8aca-3e6c6aff0399
   PHONEPE_SALT_INDEX=1
   PHONEPE_ENV=UAT
   ```

2. **Production Credentials**:
   ```env
   PHONEPE_MERCHANT_ID=your-production-merchant-id
   PHONEPE_SALT_KEY=your-production-salt-key
   PHONEPE_SALT_INDEX=1
   PHONEPE_ENV=PRODUCTION
   ```

3. **Callback URLs**:
   ```env
   PHONEPE_CALLBACK_URL=https://your-domain.com/api/v1/payments/callback
   PHONEPE_REDIRECT_URL=https://your-domain.com/payment/callback
   ```

### Environment Separation

DreamOps uses strict environment separation to ensure development features don't leak into production.

#### Environment Detection

The system uses two environment variables to determine the current mode:

1. **`NODE_ENV`** - Standard Node.js environment variable
   - `development` - Local development
   - `staging` - Staging environment
   - `production` - Production environment

2. **`NEXT_PUBLIC_DEV_MODE`** - Explicit dev mode flag
   - `true` - Enable development features
   - `false` - Disable development features (default)

#### Development Mode Features

When `NEXT_PUBLIC_DEV_MODE=true` OR `NODE_ENV=development`:

- **Automatic Pro Plan**: All new users start with Pro plan
- **All Integrations Enabled**: No plan restrictions for integrations
- **Mock Payments**: Use mock payment system
- **Debug Logging**: Enhanced logging for debugging
- **Hot Reload**: API server auto-reloads on file changes

#### Environment Files

```
.env.local          # Local development (NEXT_PUBLIC_DEV_MODE=true)
.env.staging        # Staging environment (NEXT_PUBLIC_DEV_MODE=false)
.env.production     # Production environment (NEXT_PUBLIC_DEV_MODE=false)
```

#### Configuration Loading Order

The config loader checks for environment files in this order:

1. `.env.{NODE_ENV}` (e.g., .env.production)
2. `.env.local`
3. `.env`

#### Production Safety

**Explicit Production Settings**:
```env
# .env.production
NODE_ENV=production
NEXT_PUBLIC_DEV_MODE=false
```

**Code Checks**:
```python
# Check if in development mode
is_dev_mode = (
    os.getenv("NEXT_PUBLIC_DEV_MODE", "false").lower() == "true" 
    or os.getenv("NODE_ENV", "") == "development"
)
```

#### Deployment Configuration

**Local Development**:
```bash
NODE_ENV=development ./start-dev-server.sh
# OR
NODE_ENV=development uv run python api_server.py
```

**Production Deployment**:
```bash
NODE_ENV=production uv run python api_server.py
```

**AWS/Render Environment Variables**:
- `NODE_ENV=production`
- `NEXT_PUBLIC_DEV_MODE=false`

#### Integration Plan Restrictions

| Integration | Free/Starter | Pro/Enterprise | Dev Mode |
|------------|--------------|----------------|----------|
| Kubernetes | ✅ | ✅ | ✅ |
| PagerDuty  | ✅ | ✅ | ✅ |
| Notion     | ❌ | ✅ | ✅ |
| GitHub     | ❌ | ✅ | ✅ |
| Grafana    | ❌ | ✅ | ✅ |
| Datadog    | ❌ | ✅ | ✅ |

#### Verifying Environment

```bash
# Check current environment
curl http://localhost:8000/api/v1/alert-tracking/usage/test-user | jq .account_tier
# Dev mode: "pro", Prod mode: "free"

# Check integration access
curl "http://localhost:8000/api/v1/alert-tracking/check-integration-access/test-user/notion"
# Dev mode: {"has_access": true, "reason": "Development mode - all integrations enabled"}
# Prod mode: {"has_access": false, "reason": "Integration 'notion' is not allowed on free plan"}
```

## Features & Integrations

### MCP (Model Context Protocol) Integrations

#### 1. Kubernetes Integration

Enhanced Kubernetes MCP with intelligent error detection and automated remediation:

**Features**:
- Real-time pod monitoring and management
- Automatic error detection (CrashLoopBackOff, OOM, ImagePullBackOff)
- Intelligent remediation strategies
- Resource usage analysis
- Deployment management and rollbacks

**Example Usage**:
```python
# The agent automatically detects and fixes Kubernetes issues
alert = {
    "service": "payment-service",
    "description": "Pod CrashLoopBackOff detected",
    "severity": "high"
}
# Agent will analyze logs, identify root cause, and execute fixes
```

#### 2. GitHub Integration

**Configuration**:
```env
GITHUB_TOKEN=ghp_your_github_token
GITHUB_MCP_SERVER_PATH=../../github-mcp-server/github-mcp-server
```

**Features**:
- Repository management
- Issue and PR creation
- Code search and analysis
- Automated fixes with commits

#### 3. Notion Integration

**Configuration**:
```env
NOTION_TOKEN=your-notion-token
NOTION_DATABASE_ID=your-database-id
NOTION_VERSION=2022-06-28
```

**Features**:
- Incident documentation
- Knowledge base updates
- Runbook management
- Post-mortem automation

#### 4. Grafana Integration

**Configuration**:
```env
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your-grafana-api-key
```

**Features**:
- Metric retrieval
- Dashboard analysis
- Alert correlation
- Performance insights

### YOLO Mode

YOLO (You Only Launch Once) mode enables fully autonomous operation:

```env
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
ALERT_AUTO_ACKNOWLEDGE=true
```

**Safety Mechanisms**:
- Action logging before execution
- Rollback capability
- Dry-run mode for testing
- Configurable action limits

**Testing YOLO Mode**:
```bash
# Simulate Kubernetes failures
./fuck_kubernetes.sh [1-5|all|random|clean]

# Scenarios:
# 1 - Pod crashes (CrashLoopBackOff)
# 2 - Image pull errors (ImagePullBackOff)
# 3 - OOM kills
# 4 - Deployment failures
# 5 - Service unavailability
```

## Payment System

### Overview

DreamOps uses a freemium model with PhonePe payment integration:

- **Free Tier**: 3 alerts per month
- **Starter**: ₹999/month - 50 alerts
- **Professional**: ₹4,999/month - Unlimited alerts
- **Enterprise**: Custom pricing

### Alert Tracking System

The system tracks alert usage per team:

```typescript
interface AlertUsage {
  team_id: string;
  alerts_used: number;
  alerts_limit: number;
  billing_cycle_start: Date;
  account_tier: 'free' | 'starter' | 'professional' | 'enterprise';
}
```

### Payment Flow

1. **Alert Limit Check**:
   ```typescript
   // When alert count exceeds limit
   if (alertsUsed >= alertsLimit) {
     showUpgradeModal();
   }
   ```

2. **Payment Initiation**:
   ```bash
   POST /api/v1/payments/initiate
   {
     "team_id": "team_123",
     "amount": 99900,  // ₹999 in paise
     "plan": "STARTER"
   }
   ```

3. **Payment Completion**:
   - User redirected to PhonePe
   - Callback updates team plan
   - Alert limit increased
   - UI shows Pro badge

### Testing Payments

For development, use mock payments:

```env
USE_MOCK_PAYMENTS=true
NEXT_PUBLIC_USE_MOCK_PAYMENTS=true
```

Test endpoints:
```bash
# Create mock payment
POST /api/v1/payments/test/mock-payment

# Complete mock payment
POST /api/v1/payments/test/complete-mock/{payment_id}

# View all mock transactions
GET /api/v1/payments/test/mock-transactions
```

## Deployment

### Local Development

```bash
# Start all services with mock payments
./start-dev-with-mock-payments.sh

# Or manually:
cd backend && USE_MOCK_PAYMENTS=true uv run python api_server.py
cd frontend && npm run dev
```

### Docker Setup

#### Development with Docker Compose

The project includes a complete Docker setup for local development with hot reload, automatic database setup, and all services configured.

##### Quick Start
```bash
# Start all services (frontend, backend, postgres, redis)
./docker-dev.sh up

# View logs
./docker-dev.sh logs

# Stop all services
./docker-dev.sh down
```

##### Docker Components

1. **Backend Service** (`backend/Dockerfile.dev`):
   - Python 3.12 with uv package manager
   - FastAPI with hot reload enabled
   - Kubectl installed for Kubernetes operations
   - Development environment variables pre-configured

2. **Frontend Service** (`frontend/Dockerfile.dev`):
   - Node.js 18 Alpine
   - Next.js development server
   - Hot reload enabled
   - Automatic database migrations

3. **PostgreSQL Database**:
   - PostgreSQL 16 Alpine
   - Pre-configured with development credentials
   - Persistent volume for data

4. **Redis Cache**:
   - Redis 7 Alpine
   - Used for caching and real-time features

##### Docker Commands

```bash
# Build images
./docker-dev.sh build

# Rebuild from scratch
./docker-dev.sh rebuild

# Access database
./docker-dev.sh db

# Run migrations
./docker-dev.sh migrate

# Open Drizzle Studio
./docker-dev.sh studio

# Open shell in container
./docker-dev.sh shell backend
./docker-dev.sh shell frontend
```

##### Testing Docker Setup

```bash
# Run automated test suite
./test-docker-setup.sh

# Manual health checks
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/payments/debug/environment
```

##### Docker Environment Variables

The Docker setup automatically configures:
- `NODE_ENV=development` - Development mode
- `NEXT_PUBLIC_DEV_MODE=true` - Enable all features
- `USE_MOCK_PAYMENTS=true` - Mock payment system
- `CORS_ORIGINS` - Configured for frontend access
- Database connections pre-configured

##### Troubleshooting Docker

**Port conflicts:**
```bash
# Kill processes using required ports
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
lsof -ti:5432 | xargs kill -9  # PostgreSQL
lsof -ti:6379 | xargs kill -9  # Redis
```

**View container logs:**
```bash
docker-compose logs -f backend   # Backend logs
docker-compose logs -f frontend  # Frontend logs
docker-compose logs -f postgres  # Database logs
```

**Reset everything:**
```bash
# Stop and remove all containers, networks, volumes
docker-compose down -v

# Remove images too
docker-compose down --rmi all
```

### Production Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.production.yml up -d

# Environment-specific:
docker-compose -f docker-compose.staging.yml up -d
```

### AWS Deployment

#### Terraform Deployment

1. **Prerequisites**:
   - AWS CLI configured
   - Terraform installed
   - Domain name (optional)

2. **Deploy Infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform plan -var-file=production.tfvars
   terraform apply -var-file=production.tfvars
   ```

3. **Components Deployed**:
   - ECS Fargate for backend
   - S3 + CloudFront for frontend
   - ALB for load balancing
   - RDS/Aurora for database (optional)
   - CloudWatch for monitoring
   - Secrets Manager for credentials

#### AWS Amplify Deployment

For frontend deployment via Amplify:

```yaml
version: 1
applications:
  - appRoot: frontend
    frontend:
      phases:
        preBuild:
          commands:
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: .next
        files:
          - '**/*'
      cache:
        paths:
          - 'node_modules/**/*'
```

### GitHub Actions Deployment

The project includes CI/CD workflows:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy Backend
        # Deploy to ECS
      - name: Deploy Frontend
        # Deploy to Amplify/S3
```

## Testing & Development

### Development Workflow

#### Docker Development (Recommended)

```bash
# Start all services
./docker-dev.sh up

# View logs in real-time
./docker-dev.sh logs

# Run database migrations
./docker-dev.sh migrate

# Open Drizzle Studio
./docker-dev.sh studio

# Test the setup
./test-docker-setup.sh
```

#### Manual Development

1. **Backend Development**:
   ```bash
   cd backend
   uv run python main.py  # Run CLI
   uv run python api_server.py  # Run API server
   ```

2. **Frontend Development**:
   ```bash
   cd frontend
   npm run dev  # Start development server
   npm run db:studio  # Open Drizzle Studio
   ```

3. **Testing Commands**:
   ```bash
   # Backend
   uv run pytest tests/
   uv run ruff check . --fix
   uv run mypy . --ignore-missing-imports

   # Frontend
   npm run lint
   npm run type-check
   npm test
   ```

### Testing Integrations

```bash
# Test PagerDuty webhook
curl -X POST http://localhost:8000/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -d @test_webhook_payload.json

# Test Kubernetes integration
uv run python test_k8s_pagerduty_integration.py

# Test payment flow
curl -X POST http://localhost:8000/api/v1/payments/test/mock-payment
```

### YOLO Mode Testing

```bash
# Create test namespace
kubectl create namespace fuck-kubernetes-test

# Run failure simulations
./fuck_kubernetes.sh all

# Monitor agent response
tail -f logs/agent.log

# Clean up
./fuck_kubernetes.sh clean
```

## CI/CD

### GitHub Actions Workflows

1. **Backend CI** (`.github/workflows/backend-ci.yml`):
   - Python linting and formatting
   - Type checking with mypy
   - Unit tests with pytest
   - Security scanning
   - Docker image build

2. **Frontend CI** (`.github/workflows/frontend-ci.yml`):
   - ESLint and TypeScript checks
   - Unit and integration tests
   - Build verification
   - Bundle size analysis

3. **Security Scanning** (`.github/workflows/security-scan.yml`):
   - Dependency vulnerability scanning
   - SAST with Semgrep
   - Container image scanning
   - Secret detection

4. **Deployment** (`.github/workflows/deploy.yml`):
   - Environment-specific deployments
   - Database migrations
   - Health checks
   - Rollback capability

### Environment Management

```yaml
# GitHub Secrets Required
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
ANTHROPIC_API_KEY
NEON_DATABASE_URL_STAGING
NEON_DATABASE_URL_PROD
AMPLIFY_APP_ID
```

## Troubleshooting

### Common Issues

#### 1. JSON Serialization Errors
**Problem**: `TypeError: Object of type ResolutionAction is not JSON serializable`

**Solution**:
```python
# Add to_dict() method to dataclasses
def to_dict(self) -> dict[str, Any]:
    return asdict(self)
```

#### 2. PagerDuty API Errors
**Problem**: "Requester User Not Found"

**Solution**: Ensure `PAGERDUTY_USER_EMAIL` is valid in your PagerDuty account

#### 3. Database Connection Issues
**Problem**: Connection timeouts or SSL errors

**Solution**:
- Include `?sslmode=require` in connection string
- Check Neon project is active
- Remove `&channel_binding=require` if present

#### 4. PhonePe Integration Errors
**Problem**: "Client Not Found"

**Solution**:
```env
# Use test credentials for development
PHONEPE_MERCHANT_ID=MERCHANTUAT
USE_MOCK_PAYMENTS=true
```

#### 5. Kubernetes Connection Failed
**Problem**: kubectl connection test failed

**Solution**:
- Verify kubectl is installed
- Check `~/.kube/config` exists
- Set correct context: `K8S_CONTEXT=your-context`

### Debug Tools

```bash
# Check API health
curl http://localhost:8000/health

# View payment environment
curl http://localhost:8000/api/v1/payments/debug/environment

# Test database connections
cd frontend && npm run test:db

# View agent logs
tail -f backend/logs/agent.log
```

## API Reference

### Core Endpoints

#### Health Check
```http
GET /health
```

#### Webhook Handler
```http
POST /webhook/pagerduty
Content-Type: application/json
X-Webhook-Secret: your-secret

{
  "event": {
    "event_type": "incident.triggered",
    "data": {...}
  }
}
```

### Alert Management

#### Track Alert Usage
```http
GET /api/v1/alert-tracking/usage/{team_id}
```

#### Create Manual Alert
```http
POST /api/v1/alert-tracking/alerts
{
  "team_id": "team_123",
  "title": "Database connection failed",
  "severity": "high"
}
```

### Payment Endpoints

#### Initiate Payment
```http
POST /api/v1/payments/initiate
{
  "team_id": "team_123",
  "amount": 99900,
  "plan": "STARTER"
}
```

#### Check Payment Status
```http
POST /api/v1/payments/status
{
  "merchant_transaction_id": "ORDER_123"
}
```

#### Get Plans
```http
GET /api/v1/payments/plans
```

### Dashboard API

#### Get Incidents
```http
GET /api/v1/incidents?team_id={team_id}
```

#### Get Metrics
```http
GET /api/v1/dashboard/metrics?team_id={team_id}
```

#### Get AI Actions
```http
GET /api/v1/dashboard/ai-actions?team_id={team_id}
```

## Contributing

### For Developers

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### For AI Assistants

When working with this codebase:

1. **Always check the latest documentation** before making changes
2. **Test all changes locally** before suggesting them
3. **Follow established patterns** for error handling and logging
4. **Ensure JSON serialization compatibility** for all API responses
5. **Run the pre-commit checklist**:
   ```bash
   uv run ruff check . --fix
   uv run mypy . --ignore-missing-imports
   uv run pytest tests/
   uv run python main.py
   uv run python api_server.py
   ```

### Code Style

- Python: PEP 8, type hints, async/await
- TypeScript: ESLint config, proper types
- Git: Conventional commits
- Documentation: Clear, concise, with examples

### License

MIT License - see LICENSE file for details

---

**Built with ❤️ by the DreamOps Team**

*Dream easy while AI takes your on-call duty*