#!/usr/bin/env node

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

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

// Helper to print colored text
function print(text, color = '') {
  console.log(color + text + colors.reset);
}

// Parse connection string to extract host
function extractHost(connectionString) {
  const match = connectionString.match(/@([^\/]+)\//);
  return match ? match[1] : 'unknown';
}

// Test a database connection using psql
async function testConnection(envName, connectionString) {
  print(`\n🔍 Testing ${envName} database...`, colors.bright);
  
  try {
    // Extract and display host
    const host = extractHost(connectionString);
    print(`   Host: ${host}`, colors.cyan);
    
    // Mask password in display
    const displayString = connectionString.replace(/:npg_[^@]+@/, ':***@').substring(0, 80) + '...';
    print(`   Connection: ${displayString}`);
    
    // Test connection using Node.js postgres module
    const testScript = `
      const postgres = require('postgres');
      const sql = postgres('${connectionString}', {
        ssl: 'require',
        max: 1,
        idle_timeout: 20,
        connect_timeout: 10,
      });
      
      (async () => {
        try {
          const result = await sql\`SELECT current_database(), current_user, version()\`;
          console.log(JSON.stringify({
            success: true,
            database: result[0].current_database,
            user: result[0].current_user
          }));
          await sql.end();
        } catch (error) {
          console.log(JSON.stringify({
            success: false,
            error: error.message
          }));
          process.exit(1);
        }
      })();
    `;
    
    // Write temporary test file
    const tempFile = path.join(__dirname, `.test-${envName.toLowerCase()}.js`);
    fs.writeFileSync(tempFile, testScript);
    
    // Run test
    const result = execSync(`cd frontend && node ${tempFile}`, { 
      encoding: 'utf8',
      cwd: path.join(__dirname, '..')
    });
    
    // Clean up temp file
    fs.unlinkSync(tempFile);
    
    const data = JSON.parse(result);
    if (data.success) {
      print(`   ✅ Connected successfully!`, colors.green);
      print(`   📊 Database: ${data.database}`);
      print(`   👤 User: ${data.user}`);
      return { success: true, host, database: data.database };
    } else {
      throw new Error(data.error);
    }
    
  } catch (error) {
    print(`   ❌ Connection failed: ${error.message}`, colors.red);
    return { success: false, host: extractHost(connectionString), error: error.message };
  }
}

// Load environment variables from a file
function loadEnvFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
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
  print('🚀 DreamOps Database Connection Tests', colors.bright + colors.blue);
  print('=====================================');
  print('Testing database separation for local, staging, and production environments\n');
  
  const projectRoot = path.join(__dirname, '..');
  const environments = [
    { name: 'LOCAL', backend: 'backend/.env.local', frontend: 'frontend/.env.local' },
    { name: 'STAGING', backend: 'backend/.env.staging', frontend: 'frontend/.env.staging' },
    { name: 'PRODUCTION', backend: 'backend/.env.production', frontend: 'frontend/.env.production' }
  ];
  
  const results = [];
  const hosts = new Set();
  
  // Check if postgres module is available
  try {
    require.resolve('postgres');
  } catch (e) {
    print('❌ postgres module not found. Installing...', colors.yellow);
    execSync('cd frontend && npm install postgres', { stdio: 'inherit' });
  }
  
  for (const env of environments) {
    print(`\n📂 Checking ${env.name} configuration...`, colors.bright);
    
    // Check backend file
    const backendPath = path.join(projectRoot, env.backend);
    const backendEnv = loadEnvFile(backendPath);
    
    if (!backendEnv) {
      print(`   ❌ Backend: ${env.backend} not found`, colors.red);
    } else if (!backendEnv.DATABASE_URL) {
      print(`   ❌ Backend: DATABASE_URL not configured`, colors.red);
    } else {
      print(`   ✅ Backend: ${env.backend} configured`, colors.green);
    }
    
    // Check frontend file
    const frontendPath = path.join(projectRoot, env.frontend);
    const frontendEnv = loadEnvFile(frontendPath);
    
    if (!frontendEnv) {
      print(`   ❌ Frontend: ${env.frontend} not found`, colors.red);
    } else if (!frontendEnv.POSTGRES_URL) {
      print(`   ❌ Frontend: POSTGRES_URL not configured`, colors.red);
    } else {
      print(`   ✅ Frontend: ${env.frontend} configured`, colors.green);
      
      // Test the connection
      const result = await testConnection(env.name, frontendEnv.POSTGRES_URL);
      results.push({ env: env.name, ...result });
      
      if (result.success) {
        hosts.add(result.host);
      }
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
      print(`❌ ${result.env}: Failed - ${result.error || 'Not configured'}`, colors.red);
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
      
      // Show unique hosts
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
  
  // Additional info
  if (successCount === 3 && hosts.size === 3) {
    print('\n✨ Next Steps:', colors.cyan);
    print('1. Run database migrations for each environment');
    print('2. Set up GitHub Actions secrets for staging/production');
    print('3. Update deployment scripts to use the correct environment');
  }
}

// Run the tests
runTests().catch(error => {
  print(`\n❌ Test failed: ${error.message}`, colors.red);
  process.exit(1);
});