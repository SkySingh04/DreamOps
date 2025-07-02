#!/usr/bin/env python3
"""
Check if the DreamOps agent has read your Notion documents.

This script provides several ways to verify Notion activity:
1. Check the activity summary
2. See recent reads and writes
3. Verify specific page reads
4. View live status
"""

import asyncio

import httpx

API_BASE_URL = "http://localhost:8000/api/v1/notion-activity"


async def check_activity_summary():
    """Get overall Notion activity summary."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/summary")
        if response.status_code == 200:
            data = response.json()["data"]
            print("\n📊 NOTION ACTIVITY SUMMARY")
            print("=" * 50)
            print(f"Total Operations: {data['total_operations']}")
            print(f"Pages Read: {data['pages_read']}")
            print(f"Pages Created: {data['pages_created']}")

            if data['operation_breakdown']:
                print("\nOperation Breakdown:")
                for op, count in data['operation_breakdown'].items():
                    print(f"  - {op}: {count}")

            if data['last_activity']:
                print(f"\nLast Activity: {data['last_activity']['timestamp']}")
                print(f"  Operation: {data['last_activity']['operation']}")

            return data
        else:
            print(f"Error: {response.status_code}")
            return None


async def check_recent_reads(limit: int = 10):
    """Check recent Notion page reads."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/recent-reads?limit={limit}")
        if response.status_code == 200:
            data = response.json()
            print(f"\n📖 RECENT NOTION READS (Last {limit})")
            print("=" * 50)

            if data['reads']:
                for read in data['reads']:
                    print(f"\n{read['timestamp']}")
                    print(f"  Operation: {read['operation']}")
                    details = read['details']

                    if details.get('page_id'):
                        print(f"  Page ID: {details['page_id']}")
                    if details.get('page_url'):
                        print(f"  Page URL: {details['page_url']}")
                    if details.get('query'):
                        print(f"  Search Query: {details['query']}")
                    if details.get('results_count') is not None:
                        print(f"  Results Found: {details['results_count']}")
            else:
                print("No recent reads found.")

            return data['reads']
        else:
            print(f"Error: {response.status_code}")
            return None


async def check_recent_writes(limit: int = 10):
    """Check recent Notion page writes."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/recent-writes?limit={limit}")
        if response.status_code == 200:
            data = response.json()
            print(f"\n✍️  RECENT NOTION WRITES (Last {limit})")
            print("=" * 50)

            if data['writes']:
                for write in data['writes']:
                    print(f"\n{write['timestamp']}")
                    print(f"  Operation: {write['operation']}")
                    details = write['details']

                    if details.get('page_id'):
                        print(f"  Page ID: {details['page_id']}")
                    if details.get('page_url'):
                        print(f"  Page URL: {details['page_url']}")
                    if details.get('properties'):
                        print(f"  Properties: {list(details['properties'].keys())}")
            else:
                print("No recent writes found.")

            return data['writes']
        else:
            print(f"Error: {response.status_code}")
            return None


async def verify_page_read(page_id: str):
    """Verify if a specific page has been read."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/verify-page-read/{page_id}")
        if response.status_code == 200:
            data = response.json()["data"]
            print("\n🔍 PAGE READ VERIFICATION")
            print("=" * 50)
            print(f"Page ID: {data['page_id']}")
            print(f"Has Been Read: {'✅ YES' if data['was_read'] else '❌ NO'}")

            if data['was_read']:
                print(f"Read Count: {data['read_count']} times")
                print(f"Last Read: {data['last_read']}")

                if data['read_times']:
                    print("\nRead History:")
                    for read_time in data['read_times']:
                        print(f"  - {read_time}")

            return data
        else:
            print(f"Error: {response.status_code}")
            return None


async def get_live_status():
    """Get live Notion activity status."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/live-status")
        if response.status_code == 200:
            data = response.json()["status"]
            print("\n🟢 LIVE NOTION STATUS")
            print("=" * 50)
            print(f"Currently Active: {'✅ YES' if data['is_active'] else '❌ NO'}")

            if data['last_activity']:
                print(f"Last Activity: {data['last_activity']}")

            print(f"Operations Today: {data['operations_today']}")
            print(f"Total Pages Read: {data['pages_read_total']}")
            print(f"Total Pages Created: {data['pages_created_total']}")

            if data['tracking_since']:
                print(f"Tracking Since: {data['tracking_since']}")

            return data
        else:
            print(f"Error: {response.status_code}")
            return None


async def main():
    """Main function to demonstrate all tracking capabilities."""
    print("🔍 CHECKING NOTION ACTIVITY TRACKING")
    print("====================================")
    print("This tool shows you how to verify if your agent has read Notion documents.\n")

    # Check if API server is running
    try:
        async with httpx.AsyncClient() as client:
            health = await client.get("http://localhost:8000/health")
            if health.status_code != 200:
                print("❌ API server is not running. Please start it with: uv run python api_server.py")
                return
    except:
        print("❌ Cannot connect to API server. Please start it with: uv run python api_server.py")
        return

    # Show menu
    while True:
        print("\n📋 MENU:")
        print("1. Activity Summary - See overall Notion activity")
        print("2. Recent Reads - View recently read pages")
        print("3. Recent Writes - View recently created/updated pages")
        print("4. Verify Page Read - Check if a specific page was read")
        print("5. Live Status - Get current activity status")
        print("6. Full Report - Show all information")
        print("0. Exit")

        choice = input("\nSelect an option (0-6): ").strip()

        if choice == "0":
            print("\n👋 Goodbye!")
            break
        elif choice == "1":
            await check_activity_summary()
        elif choice == "2":
            await check_recent_reads()
        elif choice == "3":
            await check_recent_writes()
        elif choice == "4":
            page_id = input("Enter Notion page ID (or URL): ").strip()
            if "/" in page_id:
                # Extract ID from URL
                page_id = page_id.split("-")[-1]
            if page_id:
                await verify_page_read(page_id)
        elif choice == "5":
            await get_live_status()
        elif choice == "6":
            # Show everything
            await check_activity_summary()
            await check_recent_reads(5)
            await check_recent_writes(5)
            await get_live_status()
        else:
            print("Invalid option. Please try again.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    asyncio.run(main())
