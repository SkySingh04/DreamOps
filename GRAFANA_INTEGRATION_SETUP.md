# Grafana MCP Integration Setup Guide

This guide explains how to set up the Grafana MCP integration with your on-call agent.

## 🚀 Quick Setup

### 1. Build the Grafana MCP Server

```bash
# Navigate to the mcp-grafana directory
cd ../mcp-grafana

# Build the binary
make build

# Verify the binary was created
ls -la dist/mcp-grafana
```

### 2. Set up Grafana Instance

You need a running Grafana instance. Options:

**Option A: Local Grafana with Docker**
```bash
docker run -d \
  -p 3000:3000 \
  --name=grafana \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana:latest
```

**Option B: Use existing Grafana instance**
- Ensure you have admin access
- Get the URL (e.g., `https://your-grafana.com`)

### 3. Get API Key

1. Open Grafana in browser: http://localhost:3000
2. Login (admin/admin by default)
3. Go to Configuration → API Keys
4. Click "New API Key"
5. Name: "OnCall Agent"
6. Role: "Admin" or "Editor"
7. Copy the generated key

### 4. Configure Environment

Update your `.env` file:

```bash
# Grafana MCP
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=eyJrIjoiWW91ckFwaUtleUhlcmU...

# Alternative: Username/Password auth
# GRAFANA_USERNAME=admin
# GRAFANA_PASSWORD=admin
```

## 🧪 Test the Integration

```bash
# Test Grafana integration specifically
cd backend
uv run python test_grafana_integration.py

# Test all integrations together
uv run python test_all_four_integrations.py
```

## 📊 What Gets Integrated

The Grafana integration provides:

### Context for Incident Analysis:
- **Dashboards**: List available dashboards
- **Metrics**: Query Prometheus/InfluxDB data
- **Alerts**: Current Grafana alerts
- **Data Sources**: Available monitoring backends

### Actions During Incidents:
- **Query Metrics**: Get specific metrics for affected services
- **Create Dashboards**: Auto-create incident dashboards
- **Silence Alerts**: Temporarily silence related alerts
- **Update Dashboards**: Add incident markers

### Automatic Features:
- **Service Metrics**: Automatically queries relevant metrics for alerted services
- **Performance Data**: Retrieves CPU, memory, request rates, error rates
- **Historical Context**: Gets metrics from before/during incident timeframe

## 🔧 Advanced Configuration

### Custom MCP Server Path
```bash
# If mcp-grafana is in a different location
GRAFANA_MCP_SERVER_PATH=/path/to/your/mcp-grafana
```

### Different Port
```bash
# If you need a different port for the MCP server
GRAFANA_MCP_PORT=8082
```

### Multiple Grafana Instances
You can configure different Grafana URLs for different environments by updating the agent configuration programmatically.

## 🐛 Troubleshooting

### "mcp-grafana binary not found"
```bash
cd ../mcp-grafana
make build
ls -la dist/  # Should show mcp-grafana binary
```

### "Connection refused to Grafana"
- Check if Grafana is running: `curl http://localhost:3000/api/health`
- Verify URL in .env matches your Grafana instance
- Check firewall/network settings

### "API Key authentication failed"
- Verify API key is correct and hasn't expired
- Ensure API key has sufficient permissions (Editor/Admin)
- Try username/password auth as fallback

### "No metrics data returned"
- Check if Grafana has data sources configured
- Verify data sources are accessible
- Check if the service name matches your monitoring labels

## 📈 Example Usage

Once configured, the integration will automatically:

1. **During alerts**: Query relevant metrics for the affected service
2. **In analysis**: Include performance data in Claude's incident analysis
3. **For context**: Show recent metric trends and anomalies
4. **In documentation**: Include metric snapshots in Notion incident pages

## 🔗 Integration Flow

```
Alert → On-Call Agent → Grafana MCP → Grafana API
                    ↓
               Claude AI Analysis
                    ↓
            Notion Documentation
         (includes metric context)
```

## 🎯 Next Steps

After setup:
1. Configure meaningful dashboards in Grafana for your services
2. Set up proper monitoring labels that match your service names
3. Create custom metric queries for your specific infrastructure
4. Test with real incidents to refine the integration