#!/usr/bin/env node
import postgres from 'postgres';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function print(text, color = '') {
  console.log(color + text + colors.reset);
}

// Extract host from connection string
function extractHost(connectionString) {
  const match = connectionString.match(/@([^\/]+)\//);
  return match ? match[1] : 'unknown';
}

// Test a database connection
async function testConnection(envName, connectionString) {
  print(`\n🔍 Testing ${envName} database...`, colors.bright);
  
  const host = extractHost(connectionString);
  print(`   Host: ${host}`, colors.cyan);
  
  // Mask password in display
  const displayString = connectionString.replace(/:npg_[^@]+@/, ':***@').substring(0, 80) + '...';
  print(`   Connection: ${displayString}`);
  
  try {
    const sql = postgres(connectionString, {
      ssl: 'require',
      max: 1,
      idle_timeout: 20,
      connect_timeout: 10,
    });
    
    // Test connection
    const result = await sql`SELECT current_database(), current_user, version()`;
    print(`   ✅ Connected successfully!`, colors.green);
    print(`   📊 Database: ${result[0].current_database}`);
    print(`   👤 User: ${result[0].current_user}`);
    
    // Create test table
    const testTable = `test_${envName.toLowerCase()}_${Date.now()}`;
    await sql`CREATE TABLE ${sql(testTable)} (
      id SERIAL PRIMARY KEY,
      environment VARCHAR(50),
      created_at TIMESTAMP DEFAULT NOW()
    )`;
    print(`   ✅ Created test table: ${testTable}`, colors.green);
    
    // Insert test data
    await sql`INSERT INTO ${sql(testTable)} (environment) VALUES (${envName})`;
    print(`   ✅ Inserted test data`);
    
    // Clean up
    await sql`DROP TABLE ${sql(testTable)}`;
    print(`   🧹 Cleaned up test table`);
    
    await sql.end();
    return { success: true, host, database: result[0].current_database };
  } catch (error) {
    print(`   ❌ Connection failed: ${error.message}`, colors.red);
    return { success: false, host, error: error.message };
  }
}

// Load environment file
function loadEnvFile(filePath) {
  try {
    const content = readFileSync(filePath, 'utf8');
    const envVars = {};
    
    content.split('\n').forEach(line => {
      if (line && !line.startsWith('#') && line.includes('=')) {
        const [key, ...valueParts] = line.split('=');
        envVars[key.trim()] = valueParts.join('=').trim();
      }
    });
    
    return envVars;
  } catch (error) {
    return null;
  }
}

// Main test function
async function runTests() {
  print(colors.bright + colors.blue + '🚀 DreamOps Database Connection Tests' + colors.reset);
  print('=====================================');
  print('Testing database separation for local, staging, and production environments\n');
  
  const environments = [
    { name: 'LOCAL', file: '.env.local' },
    { name: 'STAGING', file: '.env.staging' },
    { name: 'PRODUCTION', file: '.env.production' }
  ];
  
  const results = [];
  const hosts = new Set();
  
  for (const env of environments) {
    const envPath = join(__dirname, env.file);
    const envVars = loadEnvFile(envPath);
    
    if (!envVars) {
      print(`\n❌ ${env.name}: ${env.file} not found`, colors.red);
      results.push({ env: env.name, success: false, error: 'File not found' });
      continue;
    }
    
    if (!envVars.POSTGRES_URL) {
      print(`\n❌ ${env.name}: POSTGRES_URL not configured`, colors.red);
      results.push({ env: env.name, success: false, error: 'No POSTGRES_URL' });
      continue;
    }
    
    const result = await testConnection(env.name, envVars.POSTGRES_URL);
    results.push({ env: env.name, ...result });
    
    if (result.success) {
      hosts.add(result.host);
    }
  }
  
  // Summary
  print('\n' + '='.repeat(50), colors.bright);
  print('📊 Test Summary', colors.bright);
  print('='.repeat(50));
  
  const successCount = results.filter(r => r.success).length;
  
  results.forEach(result => {
    if (result.success) {
      print(`✅ ${result.env}: Connected to ${result.host}`, colors.green);
    } else {
      print(`❌ ${result.env}: Failed - ${result.error}`, colors.red);
    }
  });
  
  // Database separation check
  print('\n' + '='.repeat(50), colors.bright);
  print('🔒 Database Separation Check', colors.bright);
  print('='.repeat(50));
  
  if (successCount === 3) {
    if (hosts.size === 3) {
      print('✅ Perfect! All 3 environments use different database hosts.', colors.green);
      print('   Your environments are properly isolated.', colors.green);
      
      print('\n📍 Unique Database Hosts:', colors.cyan);
      Array.from(hosts).forEach((host, i) => {
        print(`   ${i + 1}. ${host}`);
      });
    } else if (hosts.size === 2) {
      print('⚠️  Warning: Only 2 unique hosts detected!', colors.yellow);
      print('   Some environments might be sharing a database.', colors.yellow);
    } else {
      print('❌ Critical: All environments use the same host!', colors.red);
      print('   Please ensure you have separate Neon projects for each environment.', colors.red);
    }
  } else {
    print(`⚠️  Only ${successCount} of 3 connections succeeded.`, colors.yellow);
    print('   Please check the failed connections above.', colors.yellow);
  }
  
  if (successCount === 3 && hosts.size === 3) {
    print('\n✨ Next Steps:', colors.cyan);
    print('1. Run database migrations for each environment');
    print('2. Set up GitHub Actions secrets for staging/production');
    print('3. Use npm run dev:local/staging/production scripts');
  }
}

// Run the tests
runTests().catch(error => {
  print(`\n❌ Test failed: ${error.message}`, colors.red);
  process.exit(1);
});