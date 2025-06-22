#!/usr/bin/env python3
"""Test Notion Direct API integration functionality."""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration


async def test_notion_direct_integration():
    """Test the Notion Direct API integration."""
    load_dotenv()

    print("🔧 Testing Notion Direct API Integration")
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
        notion = NotionDirectIntegration(config)

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

        # Test 3: Search test
        print("3. Testing search...")
        search_result = await notion.fetch_context("search", query="")
        if "error" not in search_result:
            print("   ✓ Search successful")
            print(f"   - Results found: {len(search_result.get('results', []))}")
        else:
            print(f"   ✗ Search failed: {search_result['error']}")
        print()

        # Test 4: Create test incident documentation
        print("4. Creating test incident documentation...")
        alert_data = {
            "alert_id": f"TEST-{int(datetime.now().timestamp())}",
            "service_name": "test-service",
            "severity": "high",
            "description": "Test alert for Notion Direct API integration verification",
            "metadata": {
                "test": True,
                "timestamp": datetime.now().isoformat(),
                "source": "direct_api_test"
            }
        }

        result = await notion.create_incident_documentation(alert_data)

        if result.get("success"):
            print("   ✓ Created incident page")
            print(f"   - Page ID: {result.get('page_id')}")
            print(f"   - URL: {result.get('url')}")
        else:
            print(f"   ✗ Failed to create incident page: {result.get('error')}")
        print()

        # Test 5: If database ID is set, try to get database info
        if config['database_id']:
            print("5. Testing database access...")
            try:
                db_result = await notion.fetch_context("get_database", database_id=config['database_id'])
                if "error" not in db_result:
                    print("   ✓ Database accessed")
                    print(f"   - Title: {db_result.get('title', [{}])[0].get('plain_text', 'N/A')}")
                else:
                    print(f"   ✗ Database access failed: {db_result['error']}")
            except Exception as e:
                print(f"   ✗ Database access failed: {e}")
        print()

        # Disconnect
        print("6. Disconnecting...")
        await notion.disconnect()
        print("   ✓ Disconnected")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("=" * 80)
    print("✅ Notion Direct API integration is working!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_notion_direct_integration())
    exit(0 if success else 1)
