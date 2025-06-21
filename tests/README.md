# Docker Integration Test for On-Call Agent

This Docker setup allows you to test all three MCP integrations (Notion, GitHub, and Kubernetes) together using mock services.

## 🚀 Quick Start

1. **Prerequisites**:
   - Docker and Docker Compose installed
   - `.env` file with your API keys (Anthropic, Notion, GitHub)

2. **Run the test**:
   ```bash
   # Using the shell script (Linux/Mac)
   chmod +x run-docker-test.sh
   ./run-docker-test.sh
   
   # Or directly with docker-compose
   docker-compose -f docker-compose.test.yml up --build
   ```

## 🏗️ Architecture

The test environment consists of:

- **mock-kubernetes**: Nginx server simulating Kubernetes API
- **mock-github**: Nginx server simulating GitHub API  
- **oncall-test**: The on-call agent running integration tests

## 📁 Project Structure

```
oncall-agent/
├── docker-compose.test.yml     # Docker test configuration
├── backend/
│   ├── Dockerfile.test        # Test container image
│   └── test_docker_integration.py  # Integration test script
└── mock-services/
    ├── k8s/                   # Mock Kubernetes responses
    ├── github/                # Mock GitHub responses
    ├── nginx-k8s.conf         # Kubernetes API routing
    └── nginx-github.conf      # GitHub API routing
```

## 🧪 What Gets Tested

1. **Kubernetes Integration**:
   - Pod status retrieval
   - Event logs
   - Container logs

2. **GitHub Integration**:
   - Recent commits
   - Open issues
   - GitHub Actions status

3. **Notion Integration**:
   - Real API connection
   - Incident page creation

4. **AI Analysis**:
   - Claude processes the alert with context from all integrations

## 📊 Test Results

After running, check:
- Console output for live results
- `test-results/test-summary.txt` for saved summary
- Your Notion workspace for created incident pages

## 🐛 Troubleshooting

If the test fails:

1. **Check Docker services**:
   ```bash
   docker-compose -f docker-compose.test.yml ps
   ```

2. **View logs**:
   ```bash
   docker-compose -f docker-compose.test.yml logs
   ```

3. **Verify .env file** has all required keys:
   - ANTHROPIC_API_KEY
   - NOTION_TOKEN
   - NOTION_DATABASE_ID
   - GITHUB_TOKEN

## 🧹 Cleanup

```bash
docker-compose -f docker-compose.test.yml down
```

This removes all test containers and networks.