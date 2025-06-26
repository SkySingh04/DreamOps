const postgres = require('postgres');

async function testConnections() {
  console.log('🔍 Testing Neon Database Connections\n');
  
  const connections = [
    {
      name: 'LOCAL',
      url: 'postgresql://neondb_owner:npg_WrUfbv5qu4tG@ep-wild-cherry-a8lnti87-pooler.eastus2.azure.neon.tech/neondb?sslmode=require'
    },
    {
      name: 'STAGING', 
      url: 'postgresql://neondb_owner:npg_sLKMPmqYzZ21@ep-super-mouse-a8tffxbm-pooler.eastus2.azure.neon.tech/neondb?sslmode=require'
    },
    {
      name: 'PRODUCTION',
      url: 'postgresql://neondb_owner:npg_epIjDfUscC20@ep-rough-sound-a8uzg9ns-pooler.eastus2.azure.neon.tech/neondb?sslmode=require'
    }
  ];
  
  for (const conn of connections) {
    console.log(`Testing ${conn.name}...`);
    console.log(`Host: ${conn.url.match(/@([^\/]+)/)[1]}`);
    
    try {
      // Try with minimal configuration first
      const sql = postgres(conn.url, {
        max: 1,
        connect_timeout: 60, // 60 seconds
        ssl: 'require',
        // Debug output
        debug: (connection, query, params, types) => {
          if (connection) console.log('  Debug:', connection);
        }
      });
      
      console.log('  Attempting connection...');
      const start = Date.now();
      const result = await sql`SELECT version()`;
      const duration = Date.now() - start;
      
      console.log(`  ✅ Connected in ${duration}ms`);
      console.log(`  Version: ${result[0].version.split('\n')[0]}`);
      
      await sql.end();
    } catch (error) {
      console.log(`  ❌ Failed: ${error.message}`);
      console.log(`  Error code: ${error.code}`);
      
      // Try with rejectUnauthorized: false
      try {
        console.log('  Retrying with rejectUnauthorized: false...');
        const sql = postgres(conn.url, {
          max: 1,
          connect_timeout: 60,
          ssl: { rejectUnauthorized: false }
        });
        
        const result = await sql`SELECT 1`;
        console.log('  ✅ Connected with rejectUnauthorized: false');
        await sql.end();
      } catch (error2) {
        console.log(`  ❌ Also failed: ${error2.message}`);
      }
    }
    
    console.log('');
  }
}

testConnections().catch(console.error);