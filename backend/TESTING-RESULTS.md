# PagerDuty Integration Testing Results & Guide

## Prerequisites Check

Based on the environment analysis, here's what you need to do:

### 1. Install UV Package Manager
```bash
# Install UV globally
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Or on Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Setup Commands to Run

Once UV is installed, run these commands in sequence:

```bash
cd /mnt/c/Users/incha/oncall-agent/backend

# Install dependencies
uv sync

# Start API server (Terminal 1)
uv run python api_server.py
```

## Test Scenarios to Execute

### Test 1: Basic Health Check
```bash
# Check if API is running
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "oncall-agent-api",
  "timestamp": "2024-06-21T..."
}
```

### Test 2: Single Alert Tests

Run these in Terminal 2:

```bash
# Database alert
uv run python test_pagerduty_alerts.py --type database

# Server alert
uv run python test_pagerduty_alerts.py --type server

# Security alert
uv run python test_pagerduty_alerts.py --type security

# Network alert
uv run python test_pagerduty_alerts.py --type network
```

### Test 3: Batch Testing
```bash
# Send 5 random alerts
uv run python test_pagerduty_alerts.py --batch 5
```

### Test 4: All Alert Types
```bash
# Test one of each type
uv run python test_pagerduty_alerts.py --all
```

### Test 5: Stress Test
```bash
# 10 seconds at 2 alerts/second
uv run python test_pagerduty_alerts.py --stress 10 --rate 2.0
```

## Expected Results

### 1. API Server Output
When alerts are received, you should see:
```
INFO:     127.0.0.1:xxxxx - "POST /webhook/pagerduty HTTP/1.1" 200 OK
INFO:     Processing PagerDuty webhook: incident.triggered
INFO:     Extracted context: database connection pool exhausted
INFO:     Agent processing started for alert: Database connection pool exhausted
```

### 2. Test Script Output
For each alert sent:
```
✓ Alert sent successfully: {'status': 'accepted', 'processing_id': 'proc_...'}
```

### 3. Claude's Analysis
The agent will analyze each alert and provide:
- **Severity Assessment**: Critical/High/Medium/Low
- **Root Cause Analysis**: Detailed explanation
- **Immediate Actions**: Steps to mitigate now
- **Long-term Fixes**: Permanent solutions
- **Monitoring**: What to watch for

## Sample Alert Payloads

### Database Alert Example
```json
{
  "title": "Database connection pool exhausted",
  "description": "MySQL connection pool has reached maximum capacity",
  "custom_details": {
    "connection_count": 150,
    "max_connections": 150,
    "error_rate": "45%",
    "affected_service": "user-service",
    "query_time": "5000ms",
    "database": "users_db"
  }
}
```

### Security Alert Example
```json
{
  "title": "Suspicious authentication attempts detected",
  "description": "Multiple failed login attempts from unknown IPs",
  "custom_details": {
    "failed_attempts": 150,
    "unique_ips": 45,
    "top_ip": "192.168.1.100",
    "pattern": "brute_force",
    "affected_accounts": 25
  }
}
```

## Performance Expectations

- **Single Alert Processing**: 2-5 seconds
- **Batch Processing**: Concurrent, ~3-8 seconds total
- **API Response Time**: < 500ms to acknowledge
- **Claude Analysis Time**: 2-4 seconds per alert

## Troubleshooting Common Issues

### 1. UV Not Found
```bash
# Install UV first
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then reload shell
source ~/.bashrc
```

### 2. ANTHROPIC_API_KEY Error
Make sure your .env file has the correct key:
```bash
# Check if key is set
grep ANTHROPIC_API_KEY .env
```

### 3. Port 8000 Already in Use
```bash
# Find process using port
lsof -i :8000
# Or use different port
API_PORT=8001 uv run python api_server.py
```

### 4. Connection Refused
- Ensure API server is running
- Check firewall isn't blocking localhost
- Try 127.0.0.1 instead of localhost

## Validation Checklist

- [ ] UV package manager installed
- [ ] Dependencies installed with `uv sync`
- [ ] ANTHROPIC_API_KEY configured in .env
- [ ] API server starts without errors
- [ ] Health check returns 200 OK
- [ ] Single alert test succeeds
- [ ] Batch alert test processes all alerts
- [ ] Agent provides meaningful analysis

## Next Steps After Testing

1. **Review API Logs**: Check for any warnings or errors
2. **Analyze Response Times**: Ensure acceptable latency
3. **Test Error Scenarios**: Try malformed webhooks
4. **Configure Real PagerDuty**: Set up actual webhook integration
5. **Enable Monitoring**: Add metrics and logging for production