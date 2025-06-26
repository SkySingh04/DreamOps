# Database Testing Guide - Verify Your 3 Environments

## Overview
This guide will help you verify that your three Neon databases (local, staging, production) are properly separated and working correctly.

## Prerequisites
- You've created 3 Neon projects
- You've run the setup script or manually configured your .env files
- You have the Neon connection strings ready

## Test 1: Connection Test Script

First, let's create a simple test script to verify connections:

### Create `test-db-connections.js` in your frontend directory:

```javascript
// frontend/test-db-connections.js
import postgres from 'postgres';
import dotenv from 'dotenv';
import { readFileSync } from 'fs';

// Function to test a database connection
async function testConnection(envName, connectionString) {
  console.log(`\n🔍 Testing ${envName} database...`);
  console.log(`   Connection: ${connectionString.substring(0, 50)}...`);
  
  try {
    const sql = postgres(connectionString, {
      ssl: 'require',
      max: 1,
      idle_timeout: 20,
      connect_timeout: 10,
    });
    
    // Test 1: Basic connection
    const result = await sql`SELECT version(), current_database(), current_user`;
    console.log(`   ✅ Connected successfully!`);
    console.log(`   📊 Database: ${result[0].current_database}`);
    console.log(`   👤 User: ${result[0].current_user}`);
    
    // Test 2: Check if tables exist
    const tables = await sql`
      SELECT tablename 
      FROM pg_tables 
      WHERE schemaname = 'public'
      ORDER BY tablename
    `;
    console.log(`   📋 Tables found: ${tables.length}`);
    if (tables.length > 0) {
      tables.forEach(t => console.log(`      - ${t.tablename}`));
    }
    
    // Test 3: Create a test table specific to this environment
    const testTableName = `test_${envName.toLowerCase()}_${Date.now()}`;
    await sql`
      CREATE TABLE IF NOT EXISTS ${sql(testTableName)} (
        id SERIAL PRIMARY KEY,
        environment VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `;
    console.log(`   ✅ Created test table: ${testTableName}`);
    
    // Test 4: Insert test data
    await sql`
      INSERT INTO ${sql(testTableName)} (environment) 
      VALUES (${envName})
    `;
    console.log(`   ✅ Inserted test data`);
    
    // Test 5: Read back the data
    const testData = await sql`
      SELECT * FROM ${sql(testTableName)}
    `;
    console.log(`   ✅ Retrieved test data: ${JSON.stringify(testData[0])}`);
    
    // Cleanup
    await sql`DROP TABLE ${sql(testTableName)}`;
    console.log(`   🧹 Cleaned up test table`);
    
    await sql.end();
    return true;
  } catch (error) {
    console.error(`   ❌ Connection failed: ${error.message}`);
    return false;
  }
}

// Main test function
async function runTests() {
  console.log('🚀 DreamOps Database Connection Tests');
  console.log('=====================================');
  
  const environments = [
    { name: 'LOCAL', file: '.env.local' },
    { name: 'STAGING', file: '.env.staging' },
    { name: 'PRODUCTION', file: '.env.production' }
  ];
  
  const results = [];
  
  for (const env of environments) {
    try {
      // Read the env file
      const envContent = readFileSync(env.file, 'utf8');
      const match = envContent.match(/POSTGRES_URL=(.*)/);
      
      if (match && match[1]) {
        const connectionString = match[1].trim();
        const success = await testConnection(env.name, connectionString);
        results.push({ env: env.name, success });
      } else {
        console.log(`\n❌ ${env.name}: No POSTGRES_URL found in ${env.file}`);
        results.push({ env: env.name, success: false });
      }
    } catch (error) {
      console.log(`\n❌ ${env.name}: Could not read ${env.file} - ${error.message}`);
      results.push({ env: env.name, success: false });
    }
  }
  
  // Summary
  console.log('\n📊 Test Summary');
  console.log('===============');
  results.forEach(r => {
    console.log(`${r.success ? '✅' : '❌'} ${r.env}: ${r.success ? 'Connected' : 'Failed'}`);
  });
  
  const allPassed = results.every(r => r.success);
  console.log(`\n${allPassed ? '🎉 All tests passed!' : '⚠️  Some tests failed'}`);
}

// Run the tests
runTests().catch(console.error);
```

## Test 2: Manual psql Testing

You can also test manually using psql (PostgreSQL client):

### Install psql (if needed):
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### Test each connection:
```bash
# Test LOCAL database
psql "postgresql://[your-local-connection-string]" -c "SELECT current_database();"

# Test STAGING database
psql "postgresql://[your-staging-connection-string]" -c "SELECT current_database();"

# Test PRODUCTION database
psql "postgresql://[your-production-connection-string]" -c "SELECT current_database();"
```

## Test 3: Drizzle Studio (Visual Testing)

Use Drizzle Studio to visually inspect each database:

### For LOCAL:
```bash
cd frontend
cp .env.local .env
npm run db:studio
# Opens at http://localhost:4983
```

### For STAGING:
```bash
cd frontend
POSTGRES_URL="your-staging-connection-string" npm run db:studio
```

### For PRODUCTION (be careful!):
```bash
cd frontend
POSTGRES_URL="your-production-connection-string" npm run db:studio
```

## Test 4: Data Isolation Test

This test ensures data doesn't leak between environments:

### Step 1: Create unique data in each environment

```sql
-- Run this in LOCAL (via psql or Neon dashboard)
CREATE TABLE IF NOT EXISTS environment_test (
  id SERIAL PRIMARY KEY,
  env_name VARCHAR(50),
  test_value VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO environment_test (env_name, test_value) 
VALUES ('LOCAL', 'This data should only exist in LOCAL');

-- Run similar commands for STAGING and PRODUCTION with different values
```

### Step 2: Verify isolation
```sql
-- Check each database to ensure it only has its own data
SELECT * FROM environment_test;
```

## Test 5: Migration Test

Test that migrations work independently:

### Create a test migration:
```bash
cd frontend

# Create migration
npm run db:generate

# Apply to LOCAL only
npm run db:migrate

# Check that STAGING and PROD don't have the changes
POSTGRES_URL="staging-connection" npm run db:studio
```

## Test 6: API Connection Test

Create `backend/test_db_connections.py`:

```python
import asyncio
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

async def test_connection(env_name, env_file):
    """Test database connection for a specific environment"""
    print(f"\n🔍 Testing {env_name} database...")
    
    # Load the specific env file
    load_dotenv(env_file, override=True)
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print(f"   ❌ No DATABASE_URL found in {env_file}")
        return False
    
    print(f"   Connection: {db_url[:50]}...")
    
    try:
        # Create engine
        engine = create_engine(db_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database(), version()"))
            row = result.fetchone()
            print(f"   ✅ Connected to database: {row[0]}")
            
            # Check tables
            tables_result = conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            tables = [row[0] for row in tables_result]
            print(f"   📋 Tables found: {len(tables)}")
            
            # Create test record
            test_table = f"test_{env_name.lower()}_{int(asyncio.get_event_loop().time())}"
            conn.execute(text(f"""
                CREATE TABLE {test_table} (
                    id SERIAL PRIMARY KEY,
                    environment VARCHAR(50)
                )
            """))
            conn.execute(text(f"""
                INSERT INTO {test_table} (environment) VALUES (:env)
            """), {"env": env_name})
            
            # Verify
            verify = conn.execute(text(f"SELECT * FROM {test_table}"))
            data = verify.fetchone()
            print(f"   ✅ Test data created and verified: {data}")
            
            # Cleanup
            conn.execute(text(f"DROP TABLE {test_table}"))
            print(f"   🧹 Cleaned up test table")
            
            conn.commit()
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

async def main():
    """Run all connection tests"""
    print("🚀 DreamOps Database Connection Tests")
    print("=====================================")
    
    environments = [
        ("LOCAL", ".env.local"),
        ("STAGING", ".env.staging"),
        ("PRODUCTION", ".env.production")
    ]
    
    results = []
    for env_name, env_file in environments:
        success = await test_connection(env_name, env_file)
        results.append((env_name, success))
    
    print("\n📊 Test Summary")
    print("===============")
    for env_name, success in results:
        status = "✅ Connected" if success else "❌ Failed"
        print(f"{env_name}: {status}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Test 7: Quick Visual Test

The fastest way to verify separation:

1. **Open Neon Dashboard** in 3 browser tabs
2. Navigate to each project (local, staging, prod)
3. Go to Tables view
4. Create a unique table in each:
   - LOCAL: `local_only_table`
   - STAGING: `staging_only_table`
   - PROD: `prod_only_table`
5. Refresh each tab - you should only see the table specific to that environment

## Common Issues and Solutions

### Issue: "SSL connection required"
**Solution**: Ensure your connection string includes `?sslmode=require`

### Issue: "Connection timeout"
**Solution**: Check if your IP is allowed (Neon allows all IPs by default)

### Issue: "Database does not exist"
**Solution**: Make sure you created the database in Neon dashboard

### Issue: "Permission denied"
**Solution**: Check that your connection string has the correct password

## Security Checklist

- [ ] Each environment has a unique connection string
- [ ] Production credentials are not in any .env.local files
- [ ] .gitignore includes all .env files
- [ ] Team members only have production access if needed
- [ ] Connection strings are stored securely (not in chat/email)

## Next Steps

After verifying all connections work:

1. Run initial migrations on each database
2. Set up GitHub Actions secrets
3. Configure your deployment pipeline
4. Document which database each team member should use