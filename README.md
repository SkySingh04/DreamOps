# DreamOps - AI-Powered Incident Response Platform

> Dream easy while AI takes your on-call duty - Intelligent incident response and infrastructure management powered by Claude AI

## Table of Contents

- [TODO List](#todo-list)
- [Project Overview](#project-overview)
- [Quick Start Guide](#quick-start-guide)
- [Architecture & Technical Details](#architecture--technical-details)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
  - [PagerDuty Integration](#pagerduty-integration)
  - [Kubernetes Integration Options](#kubernetes-integration-options)
  - [Notion Integration](#notion-integration)
  - [Grafana Integration](#grafana-integration-setup)
  - [Environment Separation](#environment-separation)
- [Features & Integrations](#features--integrations)
- [Alert System](#alert-system)
- [Deployment](#deployment)
  - [Docker Setup](#docker-setup)
  - [AWS Deployment](#aws-deployment)
  - [Render Deployment](#render-deployment)
- [Testing & Development](#testing--development)
- [CI/CD](#ci-cd)
- [Security Considerations](#security-considerations)
- [Performance Optimization](#performance-optimization)
- [Migration Guides](#migration-guides)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## Recent Changes (November 2025)

### Fixed: Real-time Log Streaming (SSE)
- **Issue**: Agent logs were not appearing in the frontend UI despite showing "Connected" status
- **Root Cause**: Next.js rewrites buffer HTTP responses, breaking Server-Sent Events (SSE) streaming
- **Solution**: Changed SSE connections to connect directly to the backend API (`NEXT_PUBLIC_API_URL`) instead of going through Next.js rewrites
- **Files Changed**: `frontend/lib/hooks/use-agent-logs.ts`

### Working Features
- ✅ Real-time AI agent log streaming to frontend
- ✅ Test Event button with auto-resolve (prevents disturbing on-call engineers)
- ✅ Claude model configuration (claude-sonnet-4-5-20250929)
- ✅ PagerDuty webhook integration (V3 format)
- ✅ Kubernetes MCP server setup (requires manual kubeconfig on server)
- ✅ Docker deployment with proper Node.js for MCP
- ✅ SSE streaming from backend to frontend

### Needs Work
- ⚠️ Incident Report Generation - needs proper implementation connected to AI agent output
- ⚠️ UI Revamp - needs polish and cleanup for production readiness
- ⚠️ Manual kubeconfig setup required on production server

See [todo.md](./todo.md) for detailed task tracking.

---

## TODO List

See [todo.md](./todo.md) for detailed task list with progress tracking.

## Project Overview

DreamOps is an intelligent AI-powered incident response and infrastructure management platform that automates on-call duties using Claude AI and Model Context Protocol (MCP) integrations.

### Key Features

- 🤖 **AI-Powered Incident Response**: Automatic alert analysis and remediation using Claude AI
- 🔧 **YOLO Mode**: Autonomous operation that executes fixes without human approval
- 🎯 **Smart Alert Routing**: Intelligent alert categorization and prioritization
- 🔌 **MCP Integrations**: Kubernetes, GitHub, PagerDuty, Notion, and Grafana
- 💳 **Flexible Alert System**: Free tier with 3 alerts/month
- 📊 **Real-time Dashboard**: Next.js frontend with live incident tracking
- 🚀 **Cloud-Native**: Docker, Terraform, and AWS deployment ready
- 🔒 **Enterprise Security**: Complete environment separation and secure secrets management
- 📈 **Chaos to Insights**: Turn chaos engineering results into actionable recommendations

### Technology Stack

- **Backend**: FastAPI, Python AsyncIO, uv package manager
- **Frontend**: Next.js 15, TypeScript, TailwindCSS, Drizzle ORM
- **AI**: Claude 3.5 Sonnet API, Model Context Protocol (MCP)
- **Database**: Neon PostgreSQL with environment separation
- **Infrastructure**: Docker, Terraform, AWS (ECS Fargate, S3, CloudFront)
- **Authentication**: Handled by Authentik reverse proxy (no built-in auth)
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

# Start development servers
npm run dev
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

# Alert Settings
# Free tier: 3 alerts/month
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

#### 1. Create Events API V2 Integration

1. Go to **Services** → **Service Directory**
2. Select your service (e.g., `frai-backend`)
3. Click **Integrations** tab
4. Click **Add Integration**
5. Search for **Events API V2**
6. Copy the **Integration Key** (routing key for sending events)

#### 2. Configure V3 Webhook Subscription

1. Go to **Integrations** → **Generic Webhooks (v3)**
2. Click **New Webhook**
3. Configure:
   - **Webhook URL**: `http://oncall.frai.pro:8001/webhook/pagerduty`
   - **Description**: DreamOps AI Agent Webhook
   - **Scope Type**: Service
   - **Scope**: Select your service (e.g., `frai-backend`)
   - **Event Subscription** - Select these events:
     - ✅ `incident.triggered`
     - ✅ `incident.acknowledged`
     - ✅ `incident.escalated`
     - ✅ `incident.resolved`
     - ✅ `incident.priority_updated`
4. Click **Add Webhook**
5. **Important**: Copy the webhook secret provided (optional, for signature verification)

> ⚠️ **IMPORTANT**: The webhook URL is `/webhook/pagerduty` (NOT `/api/v1/webhook/pagerduty`). The webhook router is mounted at the root level, not under the `/api/v1` prefix.

#### 3. Environment Variables

```env
# PagerDuty Configuration
PAGERDUTY_ENABLED=true
PAGERDUTY_API_KEY=your-api-key              # Optional: For API operations (acknowledge, resolve)
PAGERDUTY_USER_EMAIL=your-email@company.com  # Optional: Required if using API
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret # Optional: For signature verification
```

**Note**: The webhook integration works without API key. API key is only needed if you want DreamOps to acknowledge/resolve incidents in PagerDuty.

#### 4. Test the Integration

##### Option A: Trigger Real Incident via Events API

```bash
# Replace with your Integration Key from step 1
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H "Content-Type: application/json" \
  -d '{
  "routing_key": "YOUR_INTEGRATION_KEY",
  "event_action": "trigger",
  "dedup_key": "test-'$(date +%s)'",
  "payload": {
    "summary": "Test: High CPU usage on production server",
    "severity": "critical",
    "source": "monitoring-system",
    "custom_details": {
      "cpu_usage": "95%",
      "server": "prod-api-01"
    }
  }
}'
```

##### Option B: Direct Webhook Test (V3 Format)

```bash
curl -X POST http://localhost:8000/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -d '{
  "event": {
    "id": "test-event-123",
    "event_type": "incident.triggered",
    "resource_type": "incident",
    "occurred_at": "2025-11-25T14:00:00Z",
    "data": {
      "id": "TEST123",
      "type": "incident",
      "status": "triggered",
      "title": "Test Alert",
      "service": {
        "id": "PSVC123",
        "summary": "Test Service"
      },
      "urgency": "high"
    }
  }
}'
```

#### 5. Deployment Configuration

For bare metal deployment on port 8001:

```bash
# Docker Compose Configuration
# Expose port 8001 for webhook delivery
ports:
  - "8001:80"  # nginx → backend routing
```

**Important Notes**:
- PagerDuty's "Send Test Event" button **does NOT actually send webhooks** - it only validates the URL format
- Use Events API v2 (Option A above) to trigger real incidents that will send webhooks
- Webhook URL must be publicly accessible (no localhost)
- Custom ports like 8001 are supported
- Both HTTP and HTTPS are supported

> ⚠️ **CRITICAL: ALWAYS RESOLVE TEST INCIDENTS IMMEDIATELY!**
>
> Test incidents trigger real alerts to the on-call engineer. **NEVER leave test incidents open.**
>
> After triggering a test, immediately resolve it:
> ```bash
> curl -X POST https://events.pagerduty.com/v2/enqueue \
>   -H "Content-Type: application/json" \
>   -d '{"routing_key":"<YOUR_KEY>","event_action":"resolve","dedup_key":"<SAME_DEDUP_KEY>"}'
> ```

### Slack Integration

DreamOps posts AI analysis results as thread replies under PagerDuty incident messages in Slack.

#### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name it (e.g., "ONCALL AI") and select your workspace

#### 2. Configure Bot Permissions

In **OAuth & Permissions**, add these Bot Token Scopes:
- `chat:write` - Post messages
- `channels:history` - Read channel messages (to find PagerDuty threads)

#### 3. Install App to Workspace

Click "Install to Workspace" and authorize the app.

#### 4. Get Credentials

- **Bot Token**: Copy from OAuth & Permissions page (starts with `xoxb-`)
- **Channel ID**: Right-click channel → View details → Copy Channel ID

#### 5. Invite Bot to Channel

In Slack, go to your incidents channel and type:
```
/invite @ONCALL AI
```

#### 6. Configure Environment Variables

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx  # Optional fallback
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL_ID=C07A3NZAYSD
SLACK_CHANNEL=#oncall
SLACK_ENABLED=true
```

#### Slack Notification Format

When AI analysis completes, a concise thread reply is posted:

```
🤖 AI Analysis

Cause: Out of Memory (OOM) - Pod exceeded memory limits

Recommended Fixes:
• kubectl get pods -n production --field-selector=status.phase=Failed
• kubectl rollout restart deployment api-service -n production

View Full Report (clickable link to incident)
```

### Kubernetes Integration Options

DreamOps offers multiple ways to integrate with Kubernetes clusters:

#### 1. Standard Kubernetes Integration

The basic integration provides comprehensive cluster management:

```env
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=your-context-name
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false  # Set true for YOLO mode
```

**Available Actions**:
- Pod management (list, logs, describe, restart)
- Deployment operations (status, scale, rollback)
- Service monitoring and health checks
- Event retrieval and analysis
- Automated resolution strategies
- Resource constraint analysis

#### 2. Enhanced Kubernetes with Auto-Discovery

The enhanced integration adds intelligent cluster discovery:

```env
K8S_ENHANCED_ENABLED=true
K8S_ENHANCED_MULTI_CONTEXT=true
K8S_ENHANCED_AUTO_DISCOVER=true
K8S_ENHANCED_PERMISSION_CHECK=true
```

**Features**:
- Automatic context discovery from kubeconfig
- Multi-context support
- Permission verification
- Frontend configuration UI
- Namespace auto-discovery

#### 3. Agno Framework Integration

For remote Kubernetes management via Agno:

```env
AGNO_ENABLED=true
AGNO_GITHUB_TOKEN=ghp_your_github_token
AGNO_CONFIG_REPO=your-org/kubernetes-configs
```

**Connection Methods**:
- Service Account authentication
- Kubeconfig file authentication
- Client certificate authentication

**Setup**:
```python
# Configure remote connection
POST /api/v1/agno/configure
{
  "cluster_name": "production",
  "auth_method": "service_account",
  "credentials": {
    "token": "your-sa-token",
    "ca_cert": "base64-encoded-cert",
    "server": "https://k8s-api.example.com"
  }
}
```

#### 4. Kubernetes MCP Server

Run Kubernetes operations via MCP protocol:

```bash
# Start MCP server
./start-kubernetes-mcp-server.sh

# Or run directly
uv run python -m src.oncall_agent.mcp_integrations.kubernetes_mcp_server
```

**Available Operations**:
- get_pods, describe_pod, get_pod_logs
- get_deployments, scale_deployment, restart_deployment
- get_services, get_endpoints
- apply_manifest, delete_resource
- get_events, get_nodes

### Notion Integration

#### 1. Get Notion API Token

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Give it a name (e.g., "DreamOps AI Agent")
4. Select the workspace
5. Copy the "Internal Integration Token" (starts with `secret_`)

#### 2. Create a Database

1. In Notion, create a new page
2. Add a database (Table, Board, etc.)
3. Add these properties:
   - Title (default)
   - Status (Select: Open, In Progress, Resolved)
   - Priority (Select: Low, Medium, High, Critical)
   - Created (Date)
   - Description (Text)

#### 3. Get Database ID

1. Open your database in Notion
2. Copy the URL: `https://www.notion.so/your-workspace/[DATABASE_ID]?v=...`
3. The DATABASE_ID is the 32-character string after the workspace name

#### 4. Share Database with Integration

1. In your database, click "..." → "Add connections"
2. Search for your integration name
3. Click to add it

#### 5. Configure Environment Variables

```env
# Notion Integration
NOTION_TOKEN=secret_YOUR_INTEGRATION_TOKEN_HERE
NOTION_DATABASE_ID=YOUR_DATABASE_ID_HERE
NOTION_VERSION=2022-06-28
```

#### 6. Test the Integration

```bash
# Check integration status
curl http://localhost:8000/api/v1/integrations

# Test Notion specifically
curl -X POST http://localhost:8000/api/v1/integrations/notion/test
```

### Grafana Integration Setup

The Grafana integration provides metric retrieval and dashboard analysis:

```env
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your-grafana-api-key
```

**Features**:
- Metric retrieval
- Dashboard analysis
- Alert correlation
- Performance insights

**Testing**:
The project includes a comprehensive Grafana test suite:
```bash
cd backend/tests/integrations/grafana
docker-compose up -d
pytest test_grafana_integration.py -v
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
- **Unlimited Alerts**: No alert limits in development
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

**Features**:
- Incident documentation
- Knowledge base updates
- Runbook management
- Post-mortem automation

**Automated Documentation**:
Each incident is documented with:
- Incident title and ID
- Service affected
- Issue type and severity
- Timestamp
- Detailed metadata
- Investigation checklist
- Resolution placeholder

#### 4. Grafana Integration

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

### Chaos to Insights Flow

The platform turns chaos engineering results into actionable insights:

#### 1. Chaos Engineering Execution
```bash
# From frontend incidents page - click "Nuke Infrastructure"
# Or run directly:
./fuck_kubernetes.sh [1-5|all|random]
```

#### 2. Automatic Processing
- Chaos script creates Kubernetes issues
- Alerts sent to PagerDuty
- AI agent analyzes and remediates
- Creates detailed Notion documentation

#### 3. AI-Powered Insights

**Real-time Analysis**:
```bash
POST /api/v1/insights/analyze-chaos
```
- Incidents from last 2 hours
- Services affected
- Issue types detected
- Specific recommendations

**Infrastructure Health Report**:
```bash
GET /api/v1/insights/report
```
- Total incidents over time
- Most problematic services
- Incident type distribution
- Trend analysis
- Prioritized recommendations

#### 4. Pattern Detection
- Identifies recurring issues
- Detects time-based patterns
- Tracks incident frequency trends
- Builds knowledge base over time

## Alert System

### Overview

DreamOps uses a freemium model:

- **Free Tier**: 3 alerts per month
- **Starter**: 50 alerts/month
- **Professional**: Unlimited alerts
- **Enterprise**: Custom limits

### Alert Tracking

The system tracks alert usage per user:

```typescript
interface AlertUsage {
  user_id: string;
  alerts_used: number;
  alerts_limit: number;
  billing_cycle_start: Date;
  account_tier: 'free' | 'starter' | 'professional' | 'enterprise';
}
```

When alert count exceeds limit, users are prompted to upgrade.

## Deployment

### Local Development

```bash
# Start backend
cd backend && uv run python api_server.py

# Start frontend (in another terminal)
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
- `ALERTS_LIMIT=100` - Increased alert limit for development
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

### Render Deployment

Deploy to Render.com for a managed cloud platform experience:

#### Prerequisites
- Render.com account
- GitHub repository connected to Render
- Neon database (or other PostgreSQL)

#### Backend Deployment

1. **Create Web Service**:
   - Name: `dreamops-backend`
   - Environment: `Python`
   - Build Command: `pip install uv && uv sync`
   - Start Command: `uv run python api_server.py`

2. **Environment Variables**:
   ```env
   # Core
   ANTHROPIC_API_KEY=sk-ant-xxx
   CLAUDE_MODEL=claude-3-5-sonnet-20241022
   NODE_ENV=production
   NEXT_PUBLIC_DEV_MODE=false
   
   # Database
   DATABASE_URL=postgresql://xxx
   
   # API Configuration
   API_HOST=0.0.0.0
   API_PORT=10000
   CORS_ORIGINS=https://your-frontend.onrender.com
   
   # Integrations (as needed)
   PAGERDUTY_API_KEY=xxx
   K8S_ENABLED=true
   ```

3. **Advanced Settings**:
   - Instance Type: Standard or higher
   - Health Check Path: `/health`
   - Auto-Deploy: Yes

#### Frontend Deployment

1. **Create Static Site**:
   - Name: `dreamops-frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `out`

2. **Environment Variables**:
   ```env
   POSTGRES_URL=postgresql://xxx
   NEXT_PUBLIC_API_URL=https://dreamops-backend.onrender.com
   NODE_ENV=production
   ```

3. **Headers** (`render.yaml`):
   ```yaml
   headers:
     - path: /*
       name: X-Frame-Options
       value: DENY
     - path: /*
       name: X-Content-Type-Options
       value: nosniff
   ```

#### Post-Deployment

1. **Verify Services**:
   ```bash
   curl https://dreamops-backend.onrender.com/health
   curl https://dreamops-frontend.onrender.com
   ```

2. **Configure Webhooks**:
   Update PagerDuty webhook URL to Render backend URL

3. **Monitor Logs**:
   Check Render dashboard for deployment and runtime logs

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

### Grafana Test Suite

The project includes comprehensive Grafana integration tests:

```bash
cd backend/tests/integrations/grafana

# Start test environment
docker-compose up -d

# Run tests
pytest test_grafana_integration.py -v

# Performance benchmarks
pytest test_grafana_integration.py::test_performance -v
```

**Test Categories**:
- Connection tests
- Metric retrieval tests
- Alert integration tests
- Performance benchmarks
- Error handling tests

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

## Security Considerations

### Authentication
- **Authentication is handled by Authentik reverse proxy**
- No built-in authentication in the application
- User identity is provided via headers from Authentik
- Ensure Authentik is properly configured and secured

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
- Request validation using Pydantic models
- Rate limiting implemented
- Comprehensive audit logging

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

## Migration Guides

### kubectl to MCP Migration

When migrating from direct kubectl commands to MCP-based operations:

#### Command Mappings

| kubectl Command | MCP Tool | Parameters |
|----------------|----------|------------|
| `kubectl get pods` | `get_pods` | `namespace`, `label_selector` |
| `kubectl describe pod` | `describe_pod` | `name`, `namespace` |
| `kubectl logs` | `get_pod_logs` | `name`, `namespace`, `container` |
| `kubectl get deployments` | `get_deployments` | `namespace` |
| `kubectl scale` | `scale_deployment` | `name`, `namespace`, `replicas` |
| `kubectl rollout restart` | `restart_deployment` | `name`, `namespace` |
| `kubectl apply -f` | `apply_manifest` | `manifest` |
| `kubectl delete` | `delete_resource` | `resource_type`, `name`, `namespace` |

#### Before (Direct kubectl):
```python
result = subprocess.run(["kubectl", "get", "pods", "-n", "default"], capture_output=True)
```

#### After (MCP):
```python
result = await k8s_integration.call_tool("get_pods", {"namespace": "default"})
```

#### Migration Checklist
- [ ] Replace subprocess kubectl calls with MCP tools
- [ ] Update error handling for MCP responses
- [ ] Add proper async/await for MCP calls
- [ ] Update logging to use MCP context
- [ ] Test rollback scenarios
- [ ] Verify permissions work with MCP

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

#### 4. Kubernetes Connection Failed
**Problem**: kubectl connection test failed

**Solution**:
- Verify kubectl is installed
- Check `~/.kube/config` exists
- Set correct context: `K8S_CONTEXT=your-context`

#### 5. Notion Integration Issues

**Common Problems**:

1. **"notion integration requires NOTION_TOKEN and NOTION_DATABASE_ID"**
   - Make sure both environment variables are set
   - Restart the backend server after adding them

2. **"Failed to connect to Notion API"**
   - Check your integration token is correct
   - Ensure the token starts with `secret_`

3. **"Database not found"**
   - Verify the database ID is correct (32 characters)
   - Make sure you've shared the database with your integration

4. **"Insufficient permissions"**
   - The integration needs read and write access
   - Re-share the database with the integration

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

# Check integration status
curl http://localhost:8000/api/v1/integrations

# Monitor webhook traffic (if using ngrok)
curl http://localhost:4040/inspect/http
```

## API Reference

### Core Endpoints

#### Health Check
```http
GET /health
Response: {"status": "healthy", "version": "1.0.0"}
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
Response: {
  "team_id": "team_123",
  "alerts_used": 2,
  "alerts_limit": 3,
  "account_tier": "free"
}
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

#### Check Integration Access
```http
GET /api/v1/alert-tracking/check-integration-access/{team_id}/{integration_name}
Response: {
  "has_access": true,
  "reason": "Integration allowed on pro plan"
}
```

### Integration Endpoints

#### List Integrations
```http
GET /api/v1/integrations
Response: {
  "integrations": [
    {"name": "kubernetes", "enabled": true, "status": "connected"},
    {"name": "pagerduty", "enabled": true, "status": "connected"},
    {"name": "notion", "enabled": false, "status": "not_configured"}
  ]
}
```

#### Test Integration
```http
POST /api/v1/integrations/{name}/test
Response: {
  "success": true,
  "message": "Integration test successful"
}
```

#### Integration Health Check
```http
POST /api/v1/integrations/{name}/health
Response: {
  "healthy": true,
  "details": {...}
}
```

### Dashboard API

#### Get Incidents
```http
GET /api/v1/incidents?team_id={team_id}
Response: {
  "incidents": [{
    "id": "INC_123",
    "title": "Pod CrashLoopBackOff",
    "status": "resolved",
    "created_at": "2024-01-01T00:00:00Z"
  }]
}
```

#### Get Metrics
```http
GET /api/v1/dashboard/metrics?team_id={team_id}
Response: {
  "total_incidents": 45,
  "resolved_incidents": 40,
  "avg_resolution_time": 300,
  "uptime_percentage": 99.9
}
```

#### Get AI Actions
```http
GET /api/v1/dashboard/ai-actions?team_id={team_id}
Response: {
  "actions": [{
    "id": "ACT_123",
    "type": "pod_restart",
    "status": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  }]
}
```

### Insights API

#### Analyze Recent Chaos
```http
POST /api/v1/insights/analyze-chaos
Response: {
  "incidents_created": 3,
  "services_affected": ["oom-app", "bad-image-app"],
  "insights": ["Memory issues detected", "Image pull failures"],
  "recommendations": ["Increase memory limits", "Check registry access"]
}
```

#### Get Infrastructure Report
```http
GET /api/v1/insights/report
Response: Markdown report with analysis and recommendations
```

#### Get Service Analysis
```http
GET /api/v1/insights/analysis?service=oom-app
Response: {
  "service": "oom-app",
  "incident_count": 5,
  "issue_types": ["oom"],
  "recommendations": ["Urgent: Increase memory limits"]
}
```

### Agno Framework Endpoints

#### Configure Remote Cluster
```http
POST /api/v1/agno/configure
{
  "cluster_name": "production",
  "auth_method": "service_account",
  "credentials": {
    "token": "your-sa-token",
    "ca_cert": "base64-encoded-cert",
    "server": "https://k8s-api.example.com"
  }
}
```

#### Execute Remote Command
```http
POST /api/v1/agno/execute
{
  "cluster": "production",
  "operation": "get_pods",
  "namespace": "default"
}
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