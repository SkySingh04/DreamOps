#!/usr/bin/env python3
"""Test Notion integration directly."""

import asyncio
import os

from dotenv import load_dotenv

from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration


async def test_notion():
    """Test Notion API connection and operations."""
    load_dotenv()

    # Initialize Notion integration
    notion = NotionDirectIntegration({
        "notion_token": os.getenv("NOTION_TOKEN"),
        "database_id": os.getenv("NOTION_DATABASE_ID")
    })

    try:
        # Connect
        print("Connecting to Notion...")
        await notion.connect()
        print("✓ Connected successfully!")

        # Search for accessible pages/databases
        print("\nSearching Notion workspace...")
        search_result = await notion.fetch_context("search", query="")

        if search_result.get("results"):
            print(f"Found {len(search_result['results'])} items:")
            page_id = None
            database_id = None
            for item in search_result['results'][:5]:  # Show first 5
                obj_type = item.get('object')
                if obj_type == 'page':
                    # Get page title from properties
                    props = item.get('properties', {})
                    title_prop = None
                    for prop_name, prop_value in props.items():
                        if prop_value.get('type') == 'title':
                            title_items = prop_value.get('title', [])
                            if title_items:
                                title_prop = title_items[0].get('text', {}).get('content', 'Untitled')
                            break
                    title = title_prop or 'Untitled'
                    print(f"  - Page: {title} (ID: {item['id']})")
                    if not page_id:
                        page_id = item['id']
                elif obj_type == 'database':
                    title = item.get('title', [{}])[0].get('text', {}).get('content', 'Untitled')
                    print(f"  - Database: {title} (ID: {item['id']})")
                    if not database_id:
                        database_id = item['id']

            # Suggest adding to .env
            if page_id or database_id:
                print("\nTo use these in your integration, add to .env:")
                if database_id:
                    print(f"NOTION_DATABASE_ID={database_id}")
                elif page_id:
                    print("# For testing - use a page as parent")
                    print(f"NOTION_PAGE_ID={page_id}")
        else:
            print("No accessible pages/databases found. Please share a page with your integration.")
            print("\nTo share a page with your integration:")
            print("1. Open any Notion page")
            print("2. Click 'Share' in the top right")
            print("3. Invite your integration")

        # Disconnect
        await notion.disconnect()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_notion())
