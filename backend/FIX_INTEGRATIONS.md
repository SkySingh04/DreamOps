# Fixing MCP Integration Issues

## Quick Fix

Run this command to fix path issues:
```bash
./fix_env_paths.sh
```

## Manual Fix

### 1. GitHub MCP Integration Error
The error shows the GitHub MCP server path is incorrect for your system.

**Option A: Disable GitHub Integration (Easiest)**
Comment out the GITHUB_TOKEN in your .env file:
```bash
# GITHUB_TOKEN=your-token
```

**Option B: Install GitHub MCP Server**
```bash
# Clone the GitHub MCP server
cd ..
git clone https://github.com/github/github-mcp-server.git
cd github-mcp-server
# Follow their installation instructions
```

Then update your .env:
```bash
GITHUB_MCP_SERVER_PATH=../github-mcp-server/github-mcp-server
```

### 2. Notion MCP Integration Error
The Notion integration has a hardcoded Windows path that's been fixed in the code.

**To disable Notion integration:**
Comment out in your .env:
```bash
# NOTION_TOKEN=your-token
```

### 3. Chaos Engineering Script Error
The script is looking for a Kubernetes context but none is available.

**To fix:**
1. Install a local Kubernetes cluster (Kind, Minikube, or Docker Desktop)
2. Or connect to an existing cluster (update K8S_CONTEXT in .env)

**To disable chaos engineering:**
The feature will simply show an error in the UI but won't affect other functionality.

## Recommended .env for Local Development

```env
# Core settings
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=INFO

# Kubernetes (disable if no cluster)
K8S_ENABLED=false
# K8S_CONTEXT=kind-oncall-test

# Disable optional integrations
# GITHUB_TOKEN=
# NOTION_TOKEN=
# GRAFANA_URL=

# PagerDuty (if testing webhooks)
PAGERDUTY_ENABLED=true
PAGERDUTY_WEBHOOK_SECRET=test-secret
```

## Verifying the Fix

After fixing the .env file:

```bash
# Start the API server
uv run python api_server.py
```

You should see:
- Kubernetes integration will show as disabled if K8S_ENABLED=false
- No errors about GitHub/Notion MCP paths
- Server starts successfully on port 8000

The agent will work fine with just the Anthropic API key - other integrations are optional!