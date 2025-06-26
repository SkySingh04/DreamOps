const dns = require('dns');
const { promisify } = require('util');
const fs = require('fs');
const path = require('path');
const postgres = require('postgres');

// Color output helpers
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  reset: '\x1b[0m',
  bold: '\x1b[1m'
};

// Promisify DNS functions
const dnsResolve4 = promisify(dns.resolve4);
const dnsResolve6 = promisify(dns.resolve6);

// Load environment files
function loadEnvFile(envPath) {
  try {
    const content = fs.readFileSync(envPath, 'utf8');
    const envVars = {};
    content.split('\n').forEach(line => {
      const match = line.match(/^([^=]+)=(.*)$/);
      if (match) {
        envVars[match[1].trim()] = match[2].trim();
      }
    });
    return envVars;
  } catch (error) {
    return null;
  }
}

// Test DNS resolution
async function testDNS(hostname) {
  console.log(`${colors.cyan}Testing DNS resolution for ${hostname}...${colors.reset}`);
  
  try {
    const ipv4 = await dnsResolve4(hostname);
    console.log(`${colors.green}  ✓ IPv4 addresses: ${ipv4.join(', ')}${colors.reset}`);
  } catch (error) {
    console.log(`${colors.red}  ✗ IPv4 resolution failed: ${error.message}${colors.reset}`);
  }
  
  try {
    const ipv6 = await dnsResolve6(hostname);
    console.log(`${colors.green}  ✓ IPv6 addresses: ${ipv6.join(', ')}${colors.reset}`);
  } catch (error) {
    // IPv6 failures are often expected
    console.log(`${colors.yellow}  ⚠ IPv6 resolution failed (often normal): ${error.message}${colors.reset}`);
  }
}

// Extract hostname from connection string
function getHostFromUrl(url) {
  try {
    const match = url.match(/@([^:\/]+)/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

// Test database connection with various configurations
async function testConnection(name, connectionString, options = {}) {
  console.log(`\n${colors.bold}${colors.blue}Testing ${name} connection...${colors.reset}`);
  console.log(`${colors.cyan}Connection string: ${connectionString.replace(/:[^@]+@/, ':***@')}${colors.reset}`);
  
  const host = getHostFromUrl(connectionString);
  if (host) {
    await testDNS(host);
  }
  
  // Test different SSL configurations
  const sslConfigs = [
    { name: 'Default (from URL)', modify: url => url },
    { name: 'SSL Required', modify: url => url.replace(/\?.*$/, '?sslmode=require') },
    { name: 'SSL Preferred', modify: url => url.replace(/\?.*$/, '?sslmode=prefer') },
    { name: 'SSL Allow', modify: url => url.replace(/\?.*$/, '?sslmode=allow') },
    { name: 'SSL with rejectUnauthorized=false', modify: url => url.replace(/\?.*$/, '?sslmode=require&ssl={"rejectUnauthorized":false}') }
  ];
  
  for (const config of sslConfigs) {
    const modifiedUrl = config.modify(connectionString);
    console.log(`\n${colors.cyan}  Testing with ${config.name}...${colors.reset}`);
    
    try {
      const sql = postgres(modifiedUrl, {
        max: 1,
        idle_timeout: 20,
        connect_timeout: 30, // 30 second timeout
        ...options
      });
      
      const startTime = Date.now();
      const result = await sql`SELECT 1 as test, current_database() as db, version() as version`;
      const duration = Date.now() - startTime;
      
      console.log(`${colors.green}    ✓ Connection successful! (${duration}ms)${colors.reset}`);
      console.log(`${colors.green}    Database: ${result[0].db}${colors.reset}`);
      console.log(`${colors.green}    Version: ${result[0].version.split('\n')[0]}${colors.reset}`);
      
      await sql.end();
      return true;
    } catch (error) {
      console.log(`${colors.red}    ✗ Connection failed: ${error.message}${colors.reset}`);
      if (error.code) {
        console.log(`${colors.red}    Error code: ${error.code}${colors.reset}`);
      }
    }
  }
  
  // Try direct connection if pooler fails
  if (connectionString.includes('-pooler')) {
    console.log(`\n${colors.yellow}  Trying direct connection (without pooler)...${colors.reset}`);
    const directUrl = connectionString.replace('-pooler', '');
    try {
      const sql = postgres(directUrl, {
        max: 1,
        idle_timeout: 20,
        connect_timeout: 30,
        ssl: 'require'
      });
      
      const startTime = Date.now();
      const result = await sql`SELECT 1 as test`;
      const duration = Date.now() - startTime;
      
      console.log(`${colors.green}    ✓ Direct connection successful! (${duration}ms)${colors.reset}`);
      await sql.end();
    } catch (error) {
      console.log(`${colors.red}    ✗ Direct connection also failed: ${error.message}${colors.reset}`);
    }
  }
  
  return false;
}

// Main debug function
async function debugConnections() {
  console.log(`${colors.bold}${colors.blue}🔍 Neon Database Connection Debugger${colors.reset}`);
  console.log('=====================================\n');
  
  // Check WSL-specific issues
  console.log(`${colors.bold}${colors.cyan}Checking WSL Environment...${colors.reset}`);
  if (process.platform === 'linux' && fs.existsSync('/proc/version')) {
    const procVersion = fs.readFileSync('/proc/version', 'utf8');
    if (procVersion.toLowerCase().includes('microsoft')) {
      console.log(`${colors.yellow}  ⚠ Running in WSL environment${colors.reset}`);
      
      // Check DNS configuration
      if (fs.existsSync('/etc/resolv.conf')) {
        const resolv = fs.readFileSync('/etc/resolv.conf', 'utf8');
        console.log(`${colors.cyan}  DNS Configuration:${colors.reset}`);
        resolv.split('\n').filter(line => line.trim() && !line.startsWith('#')).forEach(line => {
          console.log(`    ${line}`);
        });
      }
    }
  }
  
  // Test connections for each environment
  const environments = [
    { name: 'LOCAL', file: '.env.local' },
    { name: 'STAGING', file: '.env.staging' },
    { name: 'PRODUCTION', file: '.env.production' }
  ];
  
  for (const env of environments) {
    const envPath = path.join(__dirname, '..', env.file);
    const envVars = loadEnvFile(envPath);
    
    if (!envVars) {
      console.log(`\n${colors.red}Cannot read ${env.file}${colors.reset}`);
      continue;
    }
    
    const dbUrl = envVars.POSTGRES_URL || envVars.DATABASE_URL;
    if (!dbUrl) {
      console.log(`\n${colors.red}No database URL found in ${env.file}${colors.reset}`);
      continue;
    }
    
    await testConnection(env.name, dbUrl);
  }
  
  // Network connectivity test
  console.log(`\n${colors.bold}${colors.cyan}Testing general network connectivity...${colors.reset}`);
  try {
    await testDNS('google.com');
    console.log(`${colors.green}  ✓ General internet connectivity OK${colors.reset}`);
  } catch (error) {
    console.log(`${colors.red}  ✗ No internet connectivity: ${error.message}${colors.reset}`);
  }
  
  // Suggestions
  console.log(`\n${colors.bold}${colors.yellow}Troubleshooting Suggestions:${colors.reset}`);
  console.log(`${colors.yellow}1. If all connections timeout, check your firewall/VPN settings${colors.reset}`);
  console.log(`${colors.yellow}2. Neon databases auto-suspend - they may need 5-10 seconds to wake up${colors.reset}`);
  console.log(`${colors.yellow}3. Try running with a VPN if you're on a restricted network${colors.reset}`);
  console.log(`${colors.yellow}4. For WSL users: Try updating /etc/resolv.conf or use Windows DNS${colors.reset}`);
  console.log(`${colors.yellow}5. Check if your IP is whitelisted in Neon dashboard${colors.reset}`);
}

// Run the debug script
debugConnections().catch(console.error);