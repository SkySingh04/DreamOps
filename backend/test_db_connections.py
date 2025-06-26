#!/usr/bin/env python3
"""
DreamOps Database Connection Tester
Tests that all three database environments are properly separated
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
import asyncpg
from dotenv import load_dotenv
import urllib.parse

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color):
    print(f"{color}{text}{Colors.ENDC}")

def parse_postgres_url(url):
    """Parse a PostgreSQL URL into components"""
    parsed = urllib.parse.urlparse(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/'),
        'ssl': 'require' if 'sslmode=require' in url else 'prefer'
    }

async def test_connection(env_name, env_file):
    """Test database connection for a specific environment"""
    print(f"\n🔍 Testing {Colors.BOLD}{env_name}{Colors.ENDC} database...")
    
    # Check if env file exists
    if not Path(env_file).exists():
        print_colored(f"   ❌ File not found: {env_file}", Colors.RED)
        print(f"   💡 Create this file with your {env_name} Neon connection string")
        return {'success': False, 'env': env_name, 'error': 'File not found'}
    
    # Load the specific env file
    load_dotenv(env_file, override=True)
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print_colored(f"   ❌ No DATABASE_URL found in {env_file}", Colors.RED)
        return {'success': False, 'env': env_name, 'error': 'No DATABASE_URL'}
    
    # Mask password in output
    masked_url = db_url[:30] + '***' + db_url[-20:] if len(db_url) > 50 else db_url
    print(f"   Connection: {masked_url}")
    
    try:
        # Parse connection details
        conn_params = parse_postgres_url(db_url)
        
        # Connect to database
        conn = await asyncpg.connect(
            host=conn_params['host'],
            port=conn_params['port'],
            user=conn_params['user'],
            password=conn_params['password'],
            database=conn_params['database'],
            ssl=conn_params['ssl']
        )
        
        # Test 1: Get database info
        db_info = await conn.fetchrow("""
            SELECT current_database() as db_name, 
                   current_user as db_user,
                   version() as db_version
        """)
        
        print_colored(f"   ✅ Connected successfully!", Colors.GREEN)
        print(f"   📊 Database: {db_info['db_name']}")
        print(f"   👤 User: {db_info['db_user']}")
        
        # Test 2: Check existing tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        print(f"   📋 Tables found: {len(tables)}")
        if tables:
            for i, table in enumerate(tables[:5]):
                print(f"      - {table['tablename']}")
            if len(tables) > 5:
                print(f"      ... and {len(tables) - 5} more")
        
        # Test 3: Create environment-specific test data
        timestamp = int(datetime.now().timestamp())
        test_table = f"test_{env_name.lower()}_{timestamp}"
        test_id = f"{env_name}-{timestamp}-test"
        
        # Create test table
        await conn.execute(f"""
            CREATE TABLE {test_table} (
                id SERIAL PRIMARY KEY,
                environment VARCHAR(50),
                test_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print_colored(f"   ✅ Created test table: {test_table}", Colors.GREEN)
        
        # Insert test data
        await conn.execute(f"""
            INSERT INTO {test_table} (environment, test_id) 
            VALUES ($1, $2)
        """, env_name, test_id)
        print(f"   ✅ Inserted test data with ID: {test_id}")
        
        # Verify data
        data = await conn.fetchrow(f"SELECT * FROM {test_table}")
        print(f"   ✅ Verified data: env={data['environment']}, id={data['test_id']}")
        
        # Check for test tables from other environments
        other_test_tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'test_%'
            AND tablename != $1
        """, test_table)
        
        if other_test_tables:
            print_colored(f"   ⚠️  Found {len(other_test_tables)} test tables from other runs", Colors.YELLOW)
            for table in other_test_tables[:3]:
                print(f"      - {table['tablename']}")
        
        # Cleanup
        await conn.execute(f"DROP TABLE {test_table}")
        print(f"   🧹 Cleaned up test table")
        
        # Close connection
        await conn.close()
        
        return {
            'success': True, 
            'env': env_name, 
            'database': db_info['db_name'],
            'host': conn_params['host']
        }
        
    except Exception as e:
        print_colored(f"   ❌ Error: {str(e)}", Colors.RED)
        return {'success': False, 'env': env_name, 'error': str(e)}

async def cleanup_old_test_tables(env_file):
    """Clean up any old test tables from previous runs"""
    load_dotenv(env_file, override=True)
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        return
    
    try:
        conn_params = parse_postgres_url(db_url)
        conn = await asyncpg.connect(
            host=conn_params['host'],
            port=conn_params['port'],
            user=conn_params['user'],
            password=conn_params['password'],
            database=conn_params['database'],
            ssl=conn_params['ssl']
        )
        
        # Find old test tables
        old_tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'test_%'
        """)
        
        if old_tables:
            print(f"\n🧹 Cleaning up {len(old_tables)} old test tables...")
            for table in old_tables:
                try:
                    await conn.execute(f"DROP TABLE IF EXISTS {table['tablename']}")
                    print(f"   Dropped: {table['tablename']}")
                except:
                    pass
        
        await conn.close()
    except:
        pass

async def main():
    """Run all connection tests"""
    print_colored("🚀 DreamOps Database Connection Tests", Colors.BOLD)
    print("=" * 50)
    print("This will verify that your 3 databases are separate and working.\n")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    environments = [
        ("LOCAL", ".env.local"),
        ("STAGING", ".env.staging"),
        ("PRODUCTION", ".env.production")
    ]
    
    # Optional: cleanup old test tables
    if "--cleanup" in sys.argv:
        for env_name, env_file in environments:
            await cleanup_old_test_tables(env_file)
    
    results = []
    databases = set()
    hosts = set()
    
    for env_name, env_file in environments:
        result = await test_connection(env_name, env_file)
        results.append(result)
        
        if result['success']:
            databases.add(result['database'])
            hosts.add(result['host'])
    
    # Summary
    print(f"\n{Colors.BOLD}📊 Test Summary{Colors.ENDC}")
    print("=" * 50)
    
    for result in results:
        if result['success']:
            print_colored(f"✅ {result['env']}: Connected to {result['database']}", Colors.GREEN)
        else:
            print_colored(f"❌ {result['env']}: Failed - {result.get('error', 'Unknown error')}", Colors.RED)
    
    # Database separation check
    print(f"\n{Colors.BOLD}🔒 Database Separation Check{Colors.ENDC}")
    print("=" * 50)
    
    success_count = sum(1 for r in results if r['success'])
    
    if success_count == 3:
        if len(databases) == 3:
            print_colored("✅ Perfect! All 3 environments use different databases.", Colors.GREEN)
            print("   Your data is properly isolated between environments.")
        elif len(databases) == 2:
            print_colored("⚠️  Warning: Only 2 unique databases detected!", Colors.YELLOW)
            print("   Some environments might be sharing a database.")
        else:
            print_colored("❌ Critical: All environments use the same database!", Colors.RED)
            print("   This is dangerous - data will be mixed between environments!")
        
        if len(hosts) > 1:
            print(f"\n📍 Detected {len(hosts)} different database hosts")
    
    elif success_count > 0:
        print_colored(f"⚠️  Only {success_count} of 3 connections succeeded.", Colors.YELLOW)
        print("   Please check the failed connections above.")
    else:
        print_colored("❌ No database connections succeeded.", Colors.RED)
        print("\n💡 Setup Instructions:")
        print("1. Create 3 Neon projects at https://neon.tech")
        print("2. Copy each connection string")
        print("3. Create .env.local, .env.staging, and .env.production files")
        print("4. Add DATABASE_URL=<your-neon-connection-string> to each file")
        print("5. Run this test again")
    
    # Additional tips
    if success_count < 3:
        print("\n💡 Troubleshooting Tips:")
        print("- Make sure your .env files exist in the backend directory")
        print("- Check that DATABASE_URL is set in each file")
        print("- Verify your Neon connection strings are correct")
        print("- Ensure your IP is allowed (Neon allows all IPs by default)")

if __name__ == "__main__":
    asyncio.run(main())