#!/usr/bin/env python3
"""Simple test for Notion integration."""

import asyncio
import os

from dotenv import load_dotenv

# Import both integrations to test
from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration


async def main():
    load_dotenv()

    print("Testing Notion Direct API Integration")
    print("=" * 50)

    config = {
        "notion_token": os.getenv("NOTION_TOKEN"),
        "database_id": os.getenv("NOTION_DATABASE_ID"),
        "notion_version": "2022-06-28"
    }

    notion = NotionDirectIntegration(config)

    try:
        # Connect
        await notion.connect()
        print(f"✓ Connected: {notion.connected}")

        # Search
        print("\nPerforming search...")
        results = await notion.fetch_context("search", query="test")
        print(f"✓ Search completed, found {len(results.get('results', []))} results")

        # Create a test page
        print("\nCreating test incident page...")
        alert_data = {
            "alert_id": "TEST-123",
            "service_name": "test-service",
            "severity": "high",
            "description": "This is a test incident",
            "metadata": {"test": True}
        }

        result = await notion.create_incident_documentation(alert_data)
        if result.get("success"):
            print(f"✓ Created page with ID: {result.get('page_id')}")
            print(f"  URL: {result.get('url')}")
        else:
            print(f"✗ Failed: {result.get('error')}")

        # Disconnect
        await notion.disconnect()
        print("\n✓ Disconnected")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
