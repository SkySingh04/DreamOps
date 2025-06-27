const dns = require('dns');
const { promisify } = require('util');
const { exec } = require('child_process');
const { promisify: promisifyExec } = require('util');
const fs = require('fs');

const execAsync = promisifyExec(exec);

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

// Test DNS with different servers
async function testDNSServer(hostname, dnsServer) {
  const resolver = new dns.Resolver();
  resolver.setServers([dnsServer]);
  
  return new Promise((resolve) => {
    resolver.resolve4(hostname, (err, addresses) => {
      if (err) {
        console.log(`  ${colors.red}✗ ${dnsServer}: ${err.message}${colors.reset}`);
        resolve(false);
      } else {
        console.log(`  ${colors.green}✓ ${dnsServer}: ${addresses.join(', ')}${colors.reset}`);
        resolve(true);
      }
    });
  });
}

// Check WSL DNS configuration
async function checkWSLDNS() {
  console.log(`${colors.bold}${colors.blue}🔍 WSL DNS Configuration Check${colors.reset}`);
  console.log('==============================\n');
  
  // Check if running in WSL
  if (process.platform === 'linux' && fs.existsSync('/proc/version')) {
    const procVersion = fs.readFileSync('/proc/version', 'utf8');
    if (!procVersion.toLowerCase().includes('microsoft')) {
      console.log(`${colors.green}Not running in WSL - skipping WSL-specific checks${colors.reset}`);
      return;
    }
  } else {
    console.log(`${colors.green}Not running in Linux/WSL - skipping WSL-specific checks${colors.reset}`);
    return;
  }
  
  // Check /etc/resolv.conf
  console.log(`${colors.cyan}Current /etc/resolv.conf:${colors.reset}`);
  if (fs.existsSync('/etc/resolv.conf')) {
    const resolv = fs.readFileSync('/etc/resolv.conf', 'utf8');
    console.log(resolv);
    
    // Check if it's a symlink
    const stats = fs.lstatSync('/etc/resolv.conf');
    if (stats.isSymbolicLink()) {
      console.log(`${colors.yellow}⚠ /etc/resolv.conf is a symlink${colors.reset}`);
    }
  }
  
  // Test Neon hostnames with different DNS servers
  const testHosts = [
    'ep-square-glade-a8zt9f77-pooler.eastus2.azure.neon.tech',
    'ep-bold-mode-a8z7ya0k-pooler.eastus2.azure.neon.tech',
    'ep-round-term-a8xc3zwk-pooler.eastus2.azure.neon.tech'
  ];
  
  const dnsServers = [
    { name: 'System Default', server: null },
    { name: 'Google DNS', server: '8.8.8.8' },
    { name: 'Cloudflare DNS', server: '1.1.1.1' },
    { name: 'OpenDNS', server: '208.67.222.222' }
  ];
  
  for (const host of testHosts) {
    console.log(`\n${colors.cyan}Testing DNS resolution for: ${host}${colors.reset}`);
    
    for (const dns of dnsServers) {
      if (dns.server) {
        await testDNSServer(host, dns.server);
      } else {
        // Test with system default
        try {
          const addresses = await promisify(require('dns').resolve4)(host);
          console.log(`  ${colors.green}✓ System Default: ${addresses.join(', ')}${colors.reset}`);
        } catch (err) {
          console.log(`  ${colors.red}✗ System Default: ${err.message}${colors.reset}`);
        }
      }
    }
  }
  
  // WSL-specific fix suggestion
  console.log(`\n${colors.bold}${colors.yellow}WSL DNS Fix Instructions:${colors.reset}`);
  console.log(`${colors.yellow}If DNS resolution is failing, try these fixes:${colors.reset}\n`);
  
  console.log(`1. ${colors.cyan}Create a custom /etc/resolv.conf:${colors.reset}`);
  console.log(`   sudo rm /etc/resolv.conf`);
  console.log(`   sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'`);
  console.log(`   sudo bash -c 'echo "nameserver 8.8.4.4" >> /etc/resolv.conf'`);
  console.log(`   sudo chattr +i /etc/resolv.conf  # Prevent WSL from overwriting`);
  
  console.log(`\n2. ${colors.cyan}Or disable automatic generation:${colors.reset}`);
  console.log(`   Add to /etc/wsl.conf:`);
  console.log(`   [network]`);
  console.log(`   generateResolvConf = false`);
  console.log(`   Then restart WSL: wsl --shutdown`);
  
  console.log(`\n3. ${colors.cyan}Use Windows host DNS:${colors.reset}`);
  console.log(`   Get Windows DNS: ipconfig /all | findstr "DNS Servers"`);
  console.log(`   Add that IP to /etc/resolv.conf`);
}

// Test network connectivity
async function testNetworkConnectivity() {
  console.log(`\n${colors.bold}${colors.blue}🌐 Network Connectivity Test${colors.reset}`);
  console.log('============================\n');
  
  const testSites = [
    { name: 'Google', host: 'google.com' },
    { name: 'Cloudflare', host: '1.1.1.1' },
    { name: 'Neon API', host: 'console.neon.tech' }
  ];
  
  for (const site of testSites) {
    try {
      const addresses = await promisify(dns.resolve4)(site.host);
      console.log(`${colors.green}✓ ${site.name} (${site.host}): ${addresses[0]}${colors.reset}`);
    } catch (err) {
      console.log(`${colors.red}✗ ${site.name} (${site.host}): ${err.message}${colors.reset}`);
    }
  }
  
  // Test with curl/ping if available
  console.log(`\n${colors.cyan}Testing with system tools:${colors.reset}`);
  
  try {
    await execAsync('ping -c 1 8.8.8.8');
    console.log(`${colors.green}✓ Ping to 8.8.8.8 successful${colors.reset}`);
  } catch {
    console.log(`${colors.red}✗ Ping to 8.8.8.8 failed${colors.reset}`);
  }
  
  try {
    const { stdout } = await execAsync('curl -s -o /dev/null -w "%{http_code}" https://console.neon.tech');
    console.log(`${colors.green}✓ HTTPS to console.neon.tech: HTTP ${stdout}${colors.reset}`);
  } catch {
    console.log(`${colors.red}✗ HTTPS to console.neon.tech failed${colors.reset}`);
  }
}

// Main function
async function main() {
  console.log(`${colors.bold}${colors.blue}🔍 DNS and Network Diagnostics${colors.reset}`);
  console.log('==============================\n');
  
  await checkWSLDNS();
  await testNetworkConnectivity();
  
  console.log(`\n${colors.bold}${colors.green}✓ DNS diagnostics complete${colors.reset}`);
}

main().catch(console.error);