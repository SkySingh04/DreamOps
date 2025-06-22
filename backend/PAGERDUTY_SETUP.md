# PagerDuty Integration Setup

## Required Configuration

To enable automatic incident resolution, you need to configure the following in your `.env` file:

### 1. PagerDuty API Key
```env
PAGERDUTY_API_KEY=your-api-key-here
```
- Generate from: PagerDuty → Configuration → API Access Keys
- Requires: Full access permissions

### 2. PagerDuty User Email
```env
PAGERDUTY_USER_EMAIL=your-email@company.com
```
- **IMPORTANT**: This MUST be a valid user email in your PagerDuty account
- The user must have permissions to acknowledge and resolve incidents
- Check your user email at: PagerDuty → My Profile

### 3. Webhook Secret (Optional)
```env
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
```
- For webhook signature verification
- Configure in: PagerDuty → Services → Your Service → Integrations → Webhooks

## YOLO Mode Behavior

In YOLO mode, the agent will:
1. **Always attempt** to acknowledge and resolve incidents
2. **Ignore PagerDuty API errors** and continue execution
3. **Force resolution** even if some remediation actions fail
4. **Log warnings** about PagerDuty errors but treat incidents as resolved

## Troubleshooting

### "Requester User Not Found" Error
This means the email in `PAGERDUTY_USER_EMAIL` is not a valid user in your PagerDuty account.

**Solution**: 
1. Log into PagerDuty
2. Go to "My Profile" 
3. Copy your email address
4. Update `PAGERDUTY_USER_EMAIL` in your `.env` file

### API Key Issues
If you see authentication errors:
1. Verify your API key has full access permissions
2. Check if the API key is still valid (not expired)
3. Ensure there are no extra spaces in the `.env` file

## Testing

To test the integration:
```bash
# Run the test script
uv run python test_pagerduty_resolution.py
```

This will attempt to acknowledge and resolve a test incident (will fail if incident doesn't exist, but shows if auth is working).