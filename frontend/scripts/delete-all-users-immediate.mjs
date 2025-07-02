import postgres from 'postgres';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
dotenv.config({ path: join(__dirname, '../.env') });

async function tableExists(sql, tableName) {
  try {
    const result = await sql`
      SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = ${tableName}
      ) as exists
    `;
    return result[0].exists;
  } catch (error) {
    console.error(`Error checking if table ${tableName} exists:`, error.message);
    return false;
  }
}

async function deleteFromTable(sql, tableName) {
  try {
    if (await tableExists(sql, tableName)) {
      const result = await sql`DELETE FROM ${sql(tableName)} RETURNING id`;
      console.log(`✓ Deleted ${result.length} records from ${tableName}`);
      return result.length;
    } else {
      console.log(`⚠️  Table ${tableName} does not exist, skipping...`);
      return 0;
    }
  } catch (error) {
    console.error(`❌ Error deleting from ${tableName}:`, error.message);
    return 0;
  }
}

async function getTableCount(sql, tableName) {
  try {
    if (await tableExists(sql, tableName)) {
      const result = await sql`SELECT COUNT(*) as count FROM ${sql(tableName)}`;
      return result[0].count;
    }
    return 0;
  } catch (error) {
    return 0;
  }
}

async function deleteAllUsers() {
  const connectionString = process.env.POSTGRES_URL || process.env.DATABASE_URL;
  
  if (!connectionString) {
    console.error('❌ POSTGRES_URL or DATABASE_URL not found in environment variables');
    process.exit(1);
  }
  
  console.log('🗑️  Starting to delete all users and related data...\n');
  
  const sql = postgres(connectionString, {
    ssl: 'require',
    max: 1,
  });
  
  try {
    // List of tables to check and delete from (in order of dependencies)
    const tables = [
      'setup_validation_logs',
      'incident_logs',
      'incidents',
      'api_keys',
      'user_api_keys',
      'team_integrations',
      'integration_audit_logs',
      'metrics',
      'ai_actions',
      'activity_logs',
      'user_setup_requirements',
      'invitations',
      'team_members',
      'teams',
      'kubernetes_credentials',
      'integrations',
      'alert_usage',
      'payment_transactions',
      'subscription_plans',
      'users'
    ];
    
    // Get current counts for existing tables
    console.log('Current data:');
    for (const table of ['users', 'teams', 'incidents', 'api_keys']) {
      const count = await getTableCount(sql, table);
      if (count > 0 || await tableExists(sql, table)) {
        console.log(`  - ${table}: ${count}`);
      }
    }
    console.log('');
    
    // Delete from each table
    console.log('Deleting related data...');
    let totalDeleted = 0;
    
    for (const table of tables) {
      const deleted = await deleteFromTable(sql, table);
      totalDeleted += deleted;
    }
    
    console.log(`\n✅ Successfully deleted ${totalDeleted} total records!`);
    
  } catch (error) {
    console.error('❌ Unexpected error:', error);
    process.exit(1);
  } finally {
    await sql.end();
  }
  
  process.exit(0);
}

// Run immediately without confirmation
deleteAllUsers();