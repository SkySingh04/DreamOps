#!/usr/bin/env python3
"""Test script to verify PagerDuty incident resolution functionality."""

import asyncio
import logging
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_pagerduty_resolution():
    """Test PagerDuty incident resolution."""
    # Import after loading env
    from src.oncall_agent.pagerduty_client import (
        PagerDutyClient,
        acknowledge_pagerduty_incident,
        resolve_pagerduty_incident,
    )

    # Check if API key is configured
    api_key = os.getenv("PAGERDUTY_API_KEY")
    if not api_key:
        logger.warning("PAGERDUTY_API_KEY not set - skipping PagerDuty tests")
        logger.info("To enable PagerDuty incident resolution, set PAGERDUTY_API_KEY in your .env file")
        return

    logger.info("✅ PagerDuty API key configured")

    # Test with a dummy incident ID (this will fail unless you have a real incident)
    test_incident_id = "TEST123"

    logger.info(f"Testing acknowledge for incident: {test_incident_id}")
    ack_result = await acknowledge_pagerduty_incident(test_incident_id)
    logger.info(f"Acknowledge result: {ack_result}")

    logger.info(f"Testing resolve for incident: {test_incident_id}")
    resolve_result = await resolve_pagerduty_incident(
        test_incident_id,
        "Test resolution from oncall-agent"
    )
    logger.info(f"Resolve result: {resolve_result}")

    # Test the client directly
    async with PagerDutyClient() as client:
        logger.info("Testing add note functionality")
        note_result = await client.add_note_to_incident(
            test_incident_id,
            "Test note from oncall-agent verification script"
        )
        logger.info(f"Add note result: {note_result}")


async def test_frontend_integration():
    """Test frontend integration fix."""
    from src.oncall_agent.frontend_integration import FrontendIntegration

    logger.info("\n🔧 Testing frontend integration...")

    # Test creating incident without integer ID
    async with FrontendIntegration() as integration:
        # This should work without passing incident_id
        action_result = await integration.record_ai_action(
            action="test_action",
            description="Testing frontend integration without incident_id",
            incident_id=None  # This is the fix - don't pass PagerDuty string ID
        )
        logger.info(f"Frontend action result (no incident_id): {action_result}")

        # Test creating an incident first
        incident_result = await integration.create_incident(
            title="Test Incident",
            description="Testing incident creation",
            severity="medium",
            source="test",
            source_id="TEST123"  # PagerDuty ID goes here
        )

        if incident_result and incident_result.get('id'):
            frontend_incident_id = incident_result['id']  # This is the integer ID
            logger.info(f"Created incident with frontend ID: {frontend_incident_id}")

            # Now we can use the integer ID for actions
            action_result2 = await integration.record_ai_action(
                action="test_action_with_id",
                description="Testing with proper incident ID",
                incident_id=frontend_incident_id  # Use the integer ID from frontend
            )
            logger.info(f"Frontend action result (with incident_id): {action_result2}")


async def main():
    """Run all tests."""
    logger.info("🚀 Testing Oncall Agent fixes...")

    # Test PagerDuty resolution
    await test_pagerduty_resolution()

    # Test frontend integration
    await test_frontend_integration()

    logger.info("\n✅ Test complete!")
    logger.info("\nSummary of fixes:")
    logger.info("1. Frontend integration now handles incident_id properly (doesn't pass PagerDuty string IDs)")
    logger.info("2. PagerDuty incidents will be acknowledged when remediation starts")
    logger.info("3. PagerDuty incidents will be resolved when remediation succeeds")
    logger.info("4. Set PAGERDUTY_API_KEY in .env to enable automatic incident resolution")


if __name__ == "__main__":
    asyncio.run(main())
