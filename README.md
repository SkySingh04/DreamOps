# Oncall AI Agent

An intelligent incident response system powered by Claude AI that automatically analyzes alerts, suggests remediation actions, and integrates with your existing infrastructure tools.

## 🏗️ Architecture

```
oncall-ai-agent/
├── backend/                    # Python AI agent backend
│   ├── src/                   # Source code
│   │   └── oncall_agent/      # Main package
│   │       ├── api.py         # FastAPI REST API
│   │       ├── agent.py       # Core agent logic
│   │       ├── config.py      # Configuration
│   │       └── mcp_integrations/  # MCP integrations
│   ├── tests/                 # Test files  
│   ├── main.py               # CLI entry point
│   └── Dockerfile.prod       # Production Docker image
├── frontend/                  # Next.js SaaS web interface
│   ├── app/                  # App router pages
│   ├── components/           # React components
│   └── lib/                  # Utilities
├── infrastructure/           # AWS deployment configs
│   └── terraform/           # Infrastructure as Code
├── .github/workflows/       # CI/CD pipelines
└── docker-compose.yml
```

## 🚀 Quick Start

### Backend Setup

```bash
cd backend
uv sync
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Run demo
uv run python main.py

# Or start API server
uv run uvicorn src.oncall_agent.api:app --reload
```

⚠️ **IMPORTANT**: Always run tests and linters before committing:
```bash
uv run ruff check . --fix
uv run mypy . --ignore-missing-imports  
uv run pytest tests/
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000 to access the web interface.

## 🎯 Features

- **AI-Powered Analysis**: Claude AI analyzes incidents and provides actionable insights
- **Real-time Dashboard**: Monitor active incidents and system health
- **MCP Integrations**: Connect to Kubernetes, GitHub, Grafana, and more
- **REST API**: FastAPI backend with automatic documentation
- **Kubernetes Debugging**: Automatic pod crash analysis and remediation
- **CI/CD Ready**: GitHub Actions workflows for automated deployment
- **AWS Native**: Terraform modules for ECS, CloudFront, and more
- **Security First**: Secrets management, security scanning, and audit logs

## 🛠️ Development Guidelines

### Pre-commit Checklist
**ALWAYS run these before finishing any task:**
1. `uv run ruff check . --fix` - Fix code style issues
2. `uv run mypy . --ignore-missing-imports` - Check types
3. `uv run pytest tests/` - Run all tests
4. `uv run python main.py` - Verify it still works

### Backend Development
- **Tech Stack**: Python, AGNO, FastAPI, AsyncIO
- **Key Files**: `src/oncall_agent/api.py`, `agent.py`
- **Testing**: Write tests for new features in `tests/`

### Frontend Development  
- **Tech Stack**: Next.js, React, Tailwind CSS
- **Testing**: `npm test` before committing
- **Linting**: `npm run lint` must pass

### Infrastructure
- **IaC**: Terraform modules in `infrastructure/terraform/`
- **CI/CD**: GitHub Actions in `.github/workflows/`
- **Monitoring**: CloudWatch dashboards and alarms

## 📊 Project Status

- ✅ Core AI agent implemented
- ✅ FastAPI REST API with endpoints
- ✅ Kubernetes MCP integration
- ✅ GitHub MCP integration
- ✅ AWS deployment configuration
- ✅ CI/CD pipelines configured
- ✅ Basic web interface scaffolded
- 🚧 Additional MCP integrations in progress
- 📅 Real-time WebSocket updates planned

## 🚀 Deployment

### GitHub Secrets Required

Add these secrets to your GitHub repository (Settings → Secrets → Actions):

1. **AWS_ACCESS_KEY_ID** - AWS access key for deployment
2. **AWS_SECRET_ACCESS_KEY** - AWS secret key  
3. **ANTHROPIC_API_KEY** - Your Anthropic API key
4. **CLOUDFRONT_DISTRIBUTION_ID** - CloudFront ID (after initial deployment)
5. **REACT_APP_API_URL** - Backend API URL (after initial deployment)

### Initial Deployment

1. Configure AWS credentials locally
2. Deploy infrastructure:
   ```bash
   cd infrastructure/terraform
   terraform init
   terraform apply
   ```
3. Note the outputs and add to GitHub Secrets
4. Push to main branch to trigger deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

## 🛠️ Development

### Running Tests

```bash
# Backend - ALWAYS run before committing!
cd backend
uv run ruff check . --fix      # Linting
uv run mypy . --ignore-missing-imports  # Type checking  
uv run pytest tests/           # Unit tests

# Frontend - ALWAYS run before committing!
cd frontend
npm run lint                    # Linting
npm run type-check             # TypeScript checking
npm test                       # Unit tests
npm run build                  # Verify build works
```

### API Development

```bash
# Start API server with auto-reload
cd backend
uv run uvicorn src.oncall_agent.api:app --reload

# View API docs
open http://localhost:8000/docs
```

### Contributing

1. Create a feature branch from `main`
2. Make your changes
3. **Run all tests and linters** (see above)
4. Submit a pull request with:
   - Clear description of changes
   - Confirmation that tests pass
   - Any new environment variables documented

## 📚 Documentation

- [Backend Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [Deployment Guide](./DEPLOYMENT.md)
- [AI Assistant Instructions](./backend/CLAUDE.md)
- [MCP Integration Guide](./backend/README.md#adding-new-mcp-integrations)

## 🔒 Security

- Never commit API keys or secrets
- Use environment variables for configuration  
- Store secrets in AWS Secrets Manager for production
- Security scanning runs automatically on every PR
- Follow OWASP security guidelines
- Enable audit logging in production
- Set `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false` by default

## 🏃 Quick Commands Reference

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
npm run lint                             # Check linting

# Docker
docker-compose up                        # Run full stack
docker build -f backend/Dockerfile.prod  # Build backend
```

## 📝 License

[TBD - Add your license here]

---

Built with ❤️ by the Oncall AI Team