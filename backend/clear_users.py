#!/usr/bin/env python3
"""Script to clear all user data from the database"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", ""))

# Remove channel_binding parameter which asyncpg doesn't support
if "&channel_binding=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "")
elif "?channel_binding=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?channel_binding=require", "")

async def clear_user_data():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Start a transaction
        async with conn.transaction():
            # First, show what we're about to delete
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            setup_req_count = await conn.fetchval("SELECT COUNT(*) FROM user_setup_requirements")
            
            print(f"About to delete:")
            print(f"- {user_count} users")
            print(f"- {setup_req_count} setup requirements")
            
            # Delete in correct order due to foreign key constraints
            
            # 1. Delete user_setup_requirements first
            deleted_reqs = await conn.execute("DELETE FROM user_setup_requirements")
            print(f"\nDeleted setup requirements: {deleted_reqs}")
            
            # 2. Delete activity_logs
            deleted_logs = await conn.execute("DELETE FROM activity_logs")
            print(f"Deleted activity logs: {deleted_logs}")
            
            # 3. Delete team_members
            deleted_members = await conn.execute("DELETE FROM team_members")
            print(f"Deleted team members: {deleted_members}")
            
            # 4. Delete api_keys
            deleted_keys = await conn.execute("DELETE FROM api_keys")
            print(f"Deleted API keys: {deleted_keys}")
            
            # 5. Delete users
            deleted_users = await conn.execute("DELETE FROM users")
            print(f"Deleted users: {deleted_users}")
            
            # 5. Delete teams (optional - only if you want to clear teams too)
            # deleted_teams = await conn.execute("DELETE FROM teams")
            # print(f"Deleted teams: {deleted_teams}")
            
            print("\n✅ All user data cleared successfully!")
            
    except Exception as e:
        print(f"\n❌ Error clearing data: {e}")
        raise
    finally:
        await conn.close()

async def verify_cleanup():
    """Verify that all data was cleared"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        setup_req_count = await conn.fetchval("SELECT COUNT(*) FROM user_setup_requirements")
        
        print(f"\nVerification:")
        print(f"- Users remaining: {user_count}")
        print(f"- Setup requirements remaining: {setup_req_count}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    print("🚨 WARNING: This will delete ALL user data from the database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() == "yes":
        asyncio.run(clear_user_data())
        asyncio.run(verify_cleanup())
    else:
        print("Operation cancelled.")