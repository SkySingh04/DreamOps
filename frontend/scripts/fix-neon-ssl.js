const fs = require('fs');
const path = require('path');

// Color output helpers
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
  bold: '\x1b[1m'
};

// Fix SSL parameters in DATABASE_URL
function fixDatabaseUrl(url) {
  if (!url || !url.startsWith('postgresql')) {
    return url;
  }
  
  // Check if it already has SSL parameters
  if (url.includes('sslmode=')) {
    // Ensure it's set to require
    return url.replace(/sslmode=\w+/, 'sslmode=require');
  }
  
  // Add SSL parameters
  const separator = url.includes('?') ? '&' : '?';
  return url + separator + 'sslmode=require';
}

// Process an environment file
function processEnvFile(filePath) {
  console.log(`\n${colors.blue}Processing ${path.basename(filePath)}...${colors.reset}`);
  
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    let modified = false;
    
    const updatedLines = lines.map(line => {
      // Match DATABASE_URL or POSTGRES_URL lines
      const match = line.match(/^((?:DATABASE_URL|POSTGRES_URL|NEXT_PUBLIC_DATABASE_URL)=)(.*)$/);
      if (match) {
        const varName = match[1];
        const originalUrl = match[2];
        const fixedUrl = fixDatabaseUrl(originalUrl);
        
        if (originalUrl !== fixedUrl) {
          console.log(`  ${colors.yellow}Updated ${varName.slice(0, -1)}${colors.reset}`);
          console.log(`    ${colors.red}From: ${originalUrl.replace(/:[^@]+@/, ':***@')}${colors.reset}`);
          console.log(`    ${colors.green}To:   ${fixedUrl.replace(/:[^@]+@/, ':***@')}${colors.reset}`);
          modified = true;
          return varName + fixedUrl;
        } else {
          console.log(`  ${colors.green}✓ ${varName.slice(0, -1)} already has SSL configured${colors.reset}`);
        }
      }
      return line;
    });
    
    if (modified) {
      // Create backup
      const backupPath = filePath + '.backup.' + Date.now();
      fs.writeFileSync(backupPath, content);
      console.log(`  ${colors.cyan}Created backup: ${path.basename(backupPath)}${colors.reset}`);
      
      // Write updated content
      fs.writeFileSync(filePath, updatedLines.join('\n'));
      console.log(`  ${colors.green}✓ File updated successfully${colors.reset}`);
    } else {
      console.log(`  ${colors.green}✓ No changes needed${colors.reset}`);
    }
    
  } catch (error) {
    console.log(`  ${colors.red}✗ Error: ${error.message}${colors.reset}`);
  }
}

// Main function
function fixNeonSSL() {
  console.log(`${colors.bold}${colors.blue}🔧 Neon SSL Configuration Fixer${colors.reset}`);
  console.log('================================\n');
  
  // Find all .env files
  const projectRoot = path.join(__dirname, '..', '..');
  const envFiles = [];
  
  // Frontend env files
  const frontendDir = path.join(projectRoot, 'frontend');
  ['.env', '.env.local', '.env.staging', '.env.production'].forEach(file => {
    const filePath = path.join(frontendDir, file);
    if (fs.existsSync(filePath)) {
      envFiles.push(filePath);
    }
  });
  
  // Backend env files
  const backendDir = path.join(projectRoot, 'backend');
  ['.env', '.env.local', '.env.staging', '.env.production'].forEach(file => {
    const filePath = path.join(backendDir, file);
    if (fs.existsSync(filePath)) {
      envFiles.push(filePath);
    }
  });
  
  console.log(`Found ${envFiles.length} environment files to check\n`);
  
  // Process each file
  envFiles.forEach(processEnvFile);
  
  console.log(`\n${colors.bold}${colors.green}✓ SSL configuration check complete${colors.reset}`);
  console.log(`${colors.cyan}All DATABASE_URL variables should now include ?sslmode=require${colors.reset}`);
}

// Run the fix
fixNeonSSL();