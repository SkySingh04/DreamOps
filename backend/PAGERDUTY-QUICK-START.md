# PagerDuty Integration Quick Start (Without Kubernetes)

This guide helps you quickly test the PagerDuty integration without needing Kubernetes.

## 🚀 Quick Start (2 minutes)

### Option 1: Automated Setup
```bash
cd backend
./quick_test_pagerduty.sh
```

This script will:
1. Set up your environment
2. Start the API server
3. Send test alerts
4. Show you the results

### Option 2: Manual Setup

#### 1. Set up environment
```bash
cd backend

# Copy simple config
cp .env.simple .env

# Edit .env and add your ANTHROPIC_API_KEY
# Replace 'your-api-key-here' with your actual key
```

#### 2. Install dependencies
```bash
uv sync
```

#### 3. Start the API server
```bash
uv run python api_server.py
```

#### 4. Send test alerts
In a new terminal:
```bash
cd backend

# Test a single alert
uv run python test_pagerduty_alerts.py

# Test specific alert types (no Kubernetes needed!)
uv run python test_pagerduty_alerts.py --type database
uv run python test_pagerduty_alerts.py --type server
uv run python test_pagerduty_alerts.py --type security
uv run python test_pagerduty_alerts.py --type network

# Test all alert types
uv run python test_pagerduty_alerts.py --all

# Send multiple alerts at once
uv run python test_pagerduty_alerts.py --batch 5

# Stress test
uv run python test_pagerduty_alerts.py --stress 10 --rate 2.0
```

## 📊 Available Alert Types (No K8s Required)

### Database Alerts
- Connection pool exhaustion
- Slow query timeouts
- High error rates

### Server Alerts  
- High CPU usage
- Memory leaks / OOM killer
- Process crashes

### Security Alerts
- Brute force attacks
- SQL injection attempts
- Suspicious authentication

### Network Alerts
- CDN latency issues
- DNS resolution failures
- Packet loss

## 🔍 Viewing Results

### 1. API Server Logs
The terminal running `api_server.py` will show:
- Incoming webhooks
- Processing status
- Any errors

### 2. Check Processing Status
```bash
curl http://localhost:8000/webhook/pagerduty/status
```

### 3. API Health Check
```bash
curl http://localhost:8000/health
```

## 📝 Understanding the Flow

1. **Test Script** generates realistic PagerDuty webhook payloads
2. **API Server** receives webhooks at `/webhook/pagerduty`
3. **Alert Parser** extracts technical details from the alert
4. **Oncall Agent** analyzes the incident using Claude AI
5. **Response** includes:
   - Root cause analysis
   - Immediate mitigation steps
   - Long-term recommendations
   - Monitoring suggestions

## 🛠️ Customization

### Add Custom Webhook Secret
For production, add webhook signature verification:
```bash
# In .env
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret-here
```

### Change Alert Urgency
```bash
# High urgency alert
uv run python test_pagerduty_alerts.py --urgency high

# Low urgency alert  
uv run python test_pagerduty_alerts.py --urgency low
```

### Test Specific Scenarios
```bash
# Database connection issues
uv run python test_pagerduty_alerts.py --type database

# Security incidents
uv run python test_pagerduty_alerts.py --type security

# Server performance
uv run python test_pagerduty_alerts.py --type server
```

## 🔧 Troubleshooting

### API Server Won't Start
- Check port 8000 is free: `lsof -i :8000`
- Check your .env file exists
- Verify ANTHROPIC_API_KEY is set

### No Response from Agent
- Ensure ANTHROPIC_API_KEY is valid
- Check API server logs for errors
- Try a simple health check: `curl http://localhost:8000/health`

### Connection Refused
- Make sure API server is running
- Check firewall settings
- Try `localhost` instead of `127.0.0.1`

## 📚 Next Steps

1. **Real PagerDuty Integration**:
   - Set up webhook in PagerDuty UI
   - Point to your public URL
   - Add webhook secret for security

2. **Enable Kubernetes** (optional):
   - See [README-KIND-SETUP.md](README-KIND-SETUP.md)
   - Adds K8s-specific alert handling

3. **Production Deployment**:
   - Use proper secrets management
   - Enable webhook signature verification
   - Set up monitoring and logging

## 💡 Tips

- Start with low `--rate` values for stress testing
- Check `api_server.log` for detailed debugging
- Use `--batch` to test concurrent alert processing
- The agent works best with detailed alert descriptions

## 🎯 Example Output

When you send a test alert, you'll see:

```
📤 Sending alert to http://localhost:8000/webhook/pagerduty
✅ Alert sent successfully!
📋 Response: {'status': 'accepted', 'processing_id': 'proc_abc123...'}

Check API server logs to see the agent's analysis!
```

The API server will show Claude's analysis including:
- Severity assessment
- Root cause analysis  
- Recommended immediate actions
- Long-term fixes
- Monitoring improvements