# PagerDuty Integration Guide

This guide covers setting up and configuring PagerDuty integration for automated incident management and resolution.

## Overview

The PagerDuty integration enables:
- Automatic incident acknowledgment
- Automated incident resolution after successful remediation
- Webhook handling for real-time incident updates
- YOLO mode support for autonomous operations

## Required Configuration

Add these environment variables to your `backend/.env` file:

```env
PAGERDUTY_API_KEY=your-api-key-here
PAGERDUTY_USER_EMAIL=your-email@company.com
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
```

### Configuration Details

1. **PAGERDUTY_API_KEY**
   - Generate from: PagerDuty → Configuration → API Access Keys
   - Requires: Full access permissions
   - Used for: Acknowledging and resolving incidents

2. **PAGERDUTY_USER_EMAIL**
   - **IMPORTANT**: Must be a valid user email in your PagerDuty account
   - The user must have permissions to acknowledge and resolve incidents
   - Check your user email at: PagerDuty → My Profile

3. **PAGERDUTY_WEBHOOK_SECRET** (Optional)
   - For webhook signature verification
   - Configure in: PagerDuty → Services → Your Service → Integrations → Webhooks

## Setup Steps

### 1. Generate API Key

1. Log into your PagerDuty account
2. Go to **Configuration** → **API Access Keys**
3. Click **Create New API Key**
4. Set permissions to **Full Access**
5. Copy the generated key to your `.env` file

### 2. Configure User Email

1. Go to **My Profile** in PagerDuty
2. Copy your exact email address
3. Add it to `PAGERDUTY_USER_EMAIL` in your `.env` file
4. Ensure this user has incident management permissions

### 3. Set Up Webhook (Optional)

1. Go to **Services** → Your Service → **Integrations**
2. Add a **Generic Webhook** integration
3. Set the webhook URL to: `https://your-api-url.com/webhook/pagerduty`
4. Generate a webhook secret and add it to your `.env` file

## Webhook Configuration

The PagerDuty webhook handler processes these event types:

- **incident.trigger**: New incident created
- **incident.acknowledge**: Incident acknowledged
- **incident.resolve**: Incident resolved
- **incident.escalate**: Incident escalated
- **incident.assign**: Incident assigned
- **incident.delegate**: Incident delegated

### Webhook URL
```
POST https://your-api-url.com/webhook/pagerduty
```

### Webhook Payload
The webhook receives PagerDuty incident data and triggers the AI agent for automated resolution.

## YOLO Mode Behavior

When YOLO mode is enabled, the PagerDuty integration:

1. **Always Attempts Operations**: Tries to acknowledge and resolve incidents regardless of API errors
2. **Ignores API Failures**: Continues execution even if PagerDuty API calls fail
3. **Forces Resolution**: Marks incidents as resolved after successful remediation
4. **Logs Warnings**: Records PagerDuty errors but doesn't stop the process

### YOLO Mode Configuration

```env
# Enable YOLO mode for autonomous operations
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
K8S_ENABLED=true
```

## Integration Workflow

1. **Incident Triggered**: PagerDuty sends webhook to the agent
2. **Agent Analysis**: AI analyzes the incident and determines remediation steps
3. **Acknowledgment**: Agent acknowledges the incident in PagerDuty
4. **Remediation**: Agent executes fix (e.g., restart pods, increase memory)
5. **Verification**: Agent verifies the fix was successful
6. **Resolution**: Agent resolves the incident in PagerDuty with details

## API Operations

### Acknowledge Incident
```python
await pagerduty_client.acknowledge_incident(
    incident_id="P1234567",
    requester_email="your-email@company.com"
)
```

### Resolve Incident
```python
await pagerduty_client.resolve_incident(
    incident_id="P1234567",
    requester_email="your-email@company.com",
    resolution_note="Fixed by AI agent: Restarted failed pod"
)
```

### Add Incident Note
```python
await pagerduty_client.add_incident_note(
    incident_id="P1234567",
    note="AI agent is investigating the issue..."
)
```

## Testing the Integration

### Test Configuration
```bash
cd backend
uv run python test_pagerduty_resolution.py
```

This script will:
1. Test API key authentication
2. Verify user email validity
3. Attempt to acknowledge a test incident
4. Show if the integration is working correctly

### Manual Testing
1. Create a test incident in PagerDuty
2. Trigger the webhook to your agent
3. Check if the agent acknowledges and resolves the incident
4. Verify the resolution notes are added

## Troubleshooting

### "Requester User Not Found" Error

**Cause**: The email in `PAGERDUTY_USER_EMAIL` is not a valid user in your PagerDuty account.

**Solution**: 
1. Log into PagerDuty
2. Go to "My Profile" 
3. Copy your exact email address
4. Update `PAGERDUTY_USER_EMAIL` in your `.env` file

### API Authentication Errors

**Cause**: API key issues or insufficient permissions.

**Solution**:
1. Verify your API key has full access permissions
2. Check if the API key is still valid (not expired)
3. Ensure there are no extra spaces in the `.env` file
4. Regenerate the API key if necessary

### Webhook Not Triggering

**Cause**: Webhook configuration issues.

**Solution**:
1. Verify the webhook URL is correct and accessible
2. Check if the webhook secret matches
3. Ensure your service is configured to send webhooks
4. Check network connectivity and firewall settings

### YOLO Mode Not Working

**Cause**: Configuration or permissions issues.

**Solution**:
1. Verify `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`
2. Check `PAGERDUTY_API_KEY` and `PAGERDUTY_USER_EMAIL` are set
3. Ensure the user has incident management permissions
4. Check agent logs for error messages

## Best Practices

### Security
- Use environment variables for sensitive data
- Rotate API keys regularly
- Use webhook secrets for verification
- Limit API key permissions to minimum required

### Monitoring
- Monitor API rate limits
- Log all PagerDuty operations
- Set up alerting for integration failures
- Track incident resolution times

### Configuration Management
- Use separate PagerDuty services for different environments
- Test integration in staging before production
- Document incident escalation procedures
- Maintain backup notification channels

## Integration Examples

### Basic Incident Handling
```python
from src.oncall_agent.mcp_integrations.pagerduty import PagerDutyIntegration

async def handle_incident(incident_data):
    pagerduty = PagerDutyIntegration()
    
    # Acknowledge the incident
    await pagerduty.acknowledge_incident(
        incident_id=incident_data['id'],
        requester_email=config.PAGERDUTY_USER_EMAIL
    )
    
    # Perform remediation
    result = await perform_remediation(incident_data)
    
    # Resolve the incident
    if result.success:
        await pagerduty.resolve_incident(
            incident_id=incident_data['id'],
            requester_email=config.PAGERDUTY_USER_EMAIL,
            resolution_note=f"Resolved by AI agent: {result.action}"
        )
```

### Advanced Workflow
```python
async def advanced_incident_workflow(incident):
    pagerduty = PagerDutyIntegration()
    
    try:
        # Add investigation note
        await pagerduty.add_incident_note(
            incident_id=incident['id'],
            note="AI agent investigating incident..."
        )
        
        # Acknowledge incident
        await pagerduty.acknowledge_incident(
            incident_id=incident['id'],
            requester_email=config.PAGERDUTY_USER_EMAIL
        )
        
        # Perform analysis and remediation
        analysis = await analyze_incident(incident)
        remediation_result = await execute_remediation(analysis)
        
        # Update with progress
        await pagerduty.add_incident_note(
            incident_id=incident['id'],
            note=f"Remediation completed: {remediation_result.description}"
        )
        
        # Resolve if successful
        if remediation_result.success:
            await pagerduty.resolve_incident(
                incident_id=incident['id'],
                requester_email=config.PAGERDUTY_USER_EMAIL,
                resolution_note=remediation_result.summary
            )
        
    except Exception as e:
        # Add error note if something fails
        await pagerduty.add_incident_note(
            incident_id=incident['id'],
            note=f"AI agent encountered error: {str(e)}"
        )
        raise
``` 