#!/usr/bin/env python3
"""Test Notion MCP integration functionality."""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

from src.oncall_agent.mcp_integrations.notion import NotionMCPIntegration


async def test_notion_integration():
    """Test the Notion MCP integration."""
    load_dotenv()

    print("🔧 Testing Notion MCP Integration")
    print("=" * 80)

    # Initialize Notion integration
    config = {
        "notion_token": os.getenv("NOTION_TOKEN"),
        "database_id": os.getenv("NOTION_DATABASE_ID"),
        "notion_version": os.getenv("NOTION_VERSION", "2022-06-28")
    }

    print("Configuration:")
    print(f"  - Token: {'✓' if config['notion_token'] else '✗'}")
    print(f"  - Database ID: {config['database_id'] or 'Not set'}")
    print(f"  - Version: {config['notion_version']}")
    print()

    try:
        notion = NotionMCPIntegration(config)

        # Test 1: Connect to Notion
        print("1. Testing connection...")
        await notion.connect()
        print(f"   ✓ Connected: {notion.connected}")
        print()

        # Test 2: Check capabilities
        print("2. Checking capabilities...")
        capabilities = await notion.get_capabilities()
        print(f"   Context types: {capabilities['context_types']}")
        print(f"   Actions: {capabilities['actions']}")
        print(f"   Features: {capabilities['features']}")
        print()

        # Test 3: Create mock incident documentation
        print("3. Creating test incident documentation...")
        alert_data = {
            "alert_id": f"TEST-{int(datetime.now().timestamp())}",
            "service_name": "test-service",
            "severity": "high",
            "description": "Test alert for Notion integration verification",
            "metadata": {
                "test": True,
                "timestamp": datetime.now().isoformat(),
                "source": "integration_test"
            }
        }

        result = await notion.create_incident_documentation(alert_data)

        if result.get("success"):
            print("   ✓ Created incident page")
            print(f"   - Page ID: {result.get('page_id')}")
            print(f"   - URL: {result.get('url')}")
            print(f"   - Created via: {result.get('created_via')}")
            if result.get('database_entry'):
                print("   - Database entry created: ✓")
        else:
            print(f"   ✗ Failed to create incident page: {result.get('error')}")
        print()

        # Test 4: Test individual context fetching
        if config['database_id']:
            print("4. Testing database context fetch...")
            try:
                db_context = await notion.fetch_context("database", database_id=config['database_id'])
                print("   ✓ Database context fetched")
                print(f"   - Title: {db_context.get('title')}")
                print(f"   - Properties: {list(db_context.get('properties', {}).keys())}")
            except Exception as e:
                print(f"   ✗ Failed to fetch database context: {e}")
        print()

        # Disconnect
        print("5. Disconnecting...")
        await notion.disconnect()
        print("   ✓ Disconnected")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("=" * 80)
    print("✅ Notion MCP integration is working!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_notion_integration())
    exit(0 if success else 1)
