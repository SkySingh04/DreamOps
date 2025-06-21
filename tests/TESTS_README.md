# On-Call Agent Tests

This directory contains all test files for the on-call agent, including integration tests and Docker-based testing infrastructure.

## 📁 Directory Structure

```
tests/
├── docker-compose.test.yml    # Docker test orchestration
├── Dockerfile.test           # Test container image
├── run-docker-test.sh       # Shell script to run Docker tests
├── mock-services/           # Mock API responses for testing
│   ├── k8s/                # Mock Kubernetes API
│   └── github/             # Mock GitHub API
├── test_*.py               # Various test scripts
└── README.md               # Docker test documentation
```

## 🧪 Test Types

### 1. **Unit Tests**
- `test_run.py` - Basic environment verification

### 2. **Integration Tests**
- `test_all_integrations.py` - Tests all MCP integrations
- `test_integrations_simple.py` - Simple integration test
- `test_three_integrations.py` - Tests Notion, GitHub, and Kubernetes together
- `test_notion.py` - Notion-specific tests
- `test_github_integration.py` - GitHub-specific tests

### 3. **Docker Tests**
- `test_docker_integration.py` - Full integration test with mock services
- Uses mock Kubernetes and GitHub APIs
- Tests real Notion integration

### 4. **Scenario Tests**
- `test_all_scenarios.py` - Various incident scenarios

## 🚀 Running Tests

### Quick Test
```bash
# From the backend directory
uv run python ../tests/test_integrations_simple.py
```

### Docker Test (Recommended)
```bash
# From the tests directory
./run-docker-test.sh

# Or from project root
cd tests && ./run-docker-test.sh
```

### Individual Integration Tests
```bash
# Test Notion
uv run python ../tests/test_notion.py

# Test all integrations
uv run python ../tests/test_all_integrations.py
```

## 🔧 Configuration

All tests use the `.env` file from the parent directory. Required keys:
- `ANTHROPIC_API_KEY`
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`
- `GITHUB_TOKEN` (optional)

## 📊 Test Results

- Console output shows real-time results
- Docker tests save results to `test-results/test-summary.txt`
- Notion tests create actual incident pages in your workspace

## 🐛 Troubleshooting

1. **Import errors**: Ensure you're running from the correct directory
2. **API failures**: Check your `.env` file has valid tokens
3. **Docker issues**: Verify Docker is installed and running

## 🧹 Cleanup

Docker tests automatically clean up containers. For manual cleanup:
```bash
docker-compose -f docker-compose.test.yml down
```