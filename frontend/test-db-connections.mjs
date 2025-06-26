// frontend/test-db-connections.mjs
import postgres from 'postgres';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

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
      tables.slice(0, 5).forEach(t => console.log(`      - ${t.tablename}`));
      if (tables.length > 5) console.log(`      ... and ${tables.length - 5} more`);
    }
    
    // Test 3: Create a test table specific to this environment
    const timestamp = Date.now();
    const testTableName = `test_${envName.toLowerCase()}_${timestamp}`;
    await sql`
      CREATE TABLE IF NOT EXISTS ${sql(testTableName)} (
        id SERIAL PRIMARY KEY,
        environment VARCHAR(50),
        test_id VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `;
    console.log(`   ✅ Created test table: ${testTableName}`);
    
    // Test 4: Insert test data
    const testId = `${envName}-${timestamp}-${Math.random().toString(36).substring(7)}`;
    await sql`
      INSERT INTO ${sql(testTableName)} (environment, test_id) 
      VALUES (${envName}, ${testId})
    `;
    console.log(`   ✅ Inserted test data with ID: ${testId}`);
    
    // Test 5: Read back the data
    const testData = await sql`
      SELECT * FROM ${sql(testTableName)}
    `;
    console.log(`   ✅ Retrieved test data: environment=${testData[0].environment}, test_id=${testData[0].test_id}`);
    
    // Test 6: Verify this is a different database
    const allTestTables = await sql`
      SELECT tablename 
      FROM pg_tables 
      WHERE schemaname = 'public' 
      AND tablename LIKE 'test_%'
      ORDER BY tablename
    `;
    console.log(`   🔍 Test tables in this database: ${allTestTables.length}`);
    allTestTables.forEach(t => console.log(`      - ${t.tablename}`));
    
    // Cleanup
    await sql`DROP TABLE ${sql(testTableName)}`;
    console.log(`   🧹 Cleaned up test table`);
    
    await sql.end();
    return { success: true, database: result[0].current_database, testId };
  } catch (error) {
    console.error(`   ❌ Connection failed: ${error.message}`);
    return { success: false, error: error.message };
  }
}

// Main test function
async function runTests() {
  console.log('🚀 DreamOps Database Connection Tests');
  console.log('=====================================');
  console.log('This will verify that your 3 databases are separate and working correctly.\n');
  
  const environments = [
    { name: 'LOCAL', file: '.env.local' },
    { name: 'STAGING', file: '.env.staging' },
    { name: 'PRODUCTION', file: '.env.production' }
  ];
  
  const results = [];
  const databases = new Set();
  
  for (const env of environments) {
    try {
      // Read the env file
      const envPath = join(__dirname, env.file);
      console.log(`📄 Reading ${env.file}...`);
      
      const envContent = readFileSync(envPath, 'utf8');
      const match = envContent.match(/POSTGRES_URL=(.*)/);
      
      if (match && match[1]) {
        const connectionString = match[1].trim();
        const result = await testConnection(env.name, connectionString);
        results.push({ env: env.name, ...result });
        
        if (result.success) {
          databases.add(result.database);
        }
      } else {
        console.log(`\n❌ ${env.name}: No POSTGRES_URL found in ${env.file}`);
        results.push({ env: env.name, success: false, error: 'No POSTGRES_URL found' });
      }
    } catch (error) {
      console.log(`\n❌ ${env.name}: Could not read ${env.file} - ${error.message}`);
      console.log(`   Make sure you've created the ${env.file} file with your Neon connection string`);
      results.push({ env: env.name, success: false, error: error.message });
    }
  }
  
  // Summary
  console.log('\n📊 Test Summary');
  console.log('===============');
  results.forEach(r => {
    console.log(`${r.success ? '✅' : '❌'} ${r.env}: ${r.success ? `Connected to ${r.database}` : `Failed - ${r.error}`}`);
  });
  
  // Verify separation
  console.log('\n🔒 Database Separation Check');
  console.log('============================');
  if (databases.size === 3) {
    console.log('✅ Perfect! All 3 environments are using different databases.');
    console.log('   Each environment has its own isolated database.');
  } else if (databases.size === 2) {
    console.log('⚠️  Warning: Only 2 unique databases detected.');
    console.log('   Some environments might be sharing a database!');
  } else if (databases.size === 1) {
    console.log('❌ Error: All environments are using the same database!');
    console.log('   This is dangerous - please create separate Neon projects.');
  }
  
  const allPassed = results.every(r => r.success) && databases.size === 3;
  console.log(`\n${allPassed ? '🎉 All tests passed! Your databases are properly separated.' : '⚠️  Some issues detected - please check the errors above.'}`);
  
  if (!allPassed) {
    console.log('\n💡 Next steps:');
    console.log('1. Make sure you have created 3 separate Neon projects');
    console.log('2. Copy the connection string from each project');
    console.log('3. Update your .env.local, .env.staging, and .env.production files');
    console.log('4. Run this test again');
  }
}

// Run the tests
runTests().catch(console.error);