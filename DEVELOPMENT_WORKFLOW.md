# Development Workflow Guide

This guide outlines the mandatory workflow for all development tasks on the Oncall Agent project.

## ⚠️ IMPORTANT: Pre-commit Requirements

**You MUST run these commands before finishing ANY task:**

```bash
# 1. Fix code style issues
uv run ruff check . --fix

# 2. Check type annotations (optional - many legacy issues exist)
uv run mypy . --ignore-missing-imports

# 3. Run all tests
uv run pytest tests/

# 4. Verify the application still runs
uv run python main.py
```

If any of these fail, you MUST fix the issues before considering your task complete.

## 🔄 Development Cycle

### 1. Start a Feature
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Install dependencies if needed
uv sync
```

### 2. Make Changes
- Write your code
- Add tests for new functionality
- Update documentation as needed

### 3. Pre-commit Validation (MANDATORY)
```bash
# Run the full validation suite
./scripts/validate.sh

# Or manually run each step:
uv run ruff check . --fix
uv run pytest tests/
uv run python main.py
```

### 4. Commit Changes
```bash
git add .
git commit -m "feat: your descriptive message"
```

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```

## 🧪 Testing Guidelines

### Running Tests
```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_kubernetes_integration.py

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Writing Tests
- Test files go in `tests/` directory
- Name test files as `test_*.py`
- Use pytest fixtures for common setup
- Mock external dependencies

## 🎯 Code Quality Standards

### Linting
- We use `ruff` for code style enforcement
- Configuration is in `pyproject.toml`
- Auto-fix available with `--fix` flag

### Type Checking
- Type hints are required for all new code
- Use `mypy` for validation
- Legacy code may have type errors - fix them when touching those files

### Documentation
- All public functions need docstrings
- Update README when adding features
- Document configuration changes in `.env.example`

## 🚀 Running the Application

### Development Mode
```bash
# Run CLI demo
uv run python main.py

# Run API server with auto-reload
uv run uvicorn src.oncall_agent.api:app --reload
```

### Testing Different Scenarios
```bash
# Test all K8s scenarios
uv run python test_all_scenarios.py all

# Test specific scenario
uv run python test_all_scenarios.py oom
```

## 📋 Checklist Before PR

- [ ] All tests pass: `uv run pytest tests/`
- [ ] Code is linted: `uv run ruff check .`
- [ ] Application runs: `uv run python main.py`
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages follow conventional format

## 🔧 Common Commands

```bash
# Backend
uv run python main.py                    # Run demo
uv run uvicorn src.oncall_agent.api:app # Start API
uv run pytest tests/                     # Run tests
uv run ruff check . --fix               # Fix linting

# Docker
docker build -f Dockerfile.prod .        # Build production image
docker-compose up                        # Run full stack

# Utilities
uv add <package>                         # Add dependency
uv add --dev <package>                   # Add dev dependency
```

## ⚡ Quick Validation Script

Create this script as `scripts/validate.sh`:

```bash
#!/bin/bash
set -e

echo "🔍 Running linter..."
uv run ruff check . --fix

echo "🧪 Running tests..."
uv run pytest tests/

echo "🚀 Verifying application..."
uv run python main.py &
PID=$!
sleep 5
kill $PID

echo "✅ All checks passed!"
```

Make it executable: `chmod +x scripts/validate.sh`

## 🚨 CI/CD Integration

The same checks run in CI/CD:
- Pull requests trigger test suite
- Main branch deployments require all tests to pass
- Security scans run on every push

## 💡 Tips

1. Run tests frequently during development
2. Use `--fix` flag with ruff to auto-fix issues
3. Check API docs at http://localhost:8000/docs when running
4. Use pre-commit hooks for automatic validation (coming soon)

Remember: **Quality over speed**. Take time to ensure your code meets all standards before submitting.