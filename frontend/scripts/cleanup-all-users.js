import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { users, userApiKeys, userSetupRequirements, setupValidationLogs, activityLogs, incidents, incidentLogs, aiActions, integrations } from '../lib/db/schema';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
dotenv.config({ path: join(__dirname, '..', '.env.local') });

async function cleanupAllUsers() {
  const databaseUrl = process.env.DATABASE_URL;
  
  if (!databaseUrl) {
    console.error('DATABASE_URL is not set in .env.local');
    process.exit(1);
  }

  console.log('Connecting to database...');
  const client = postgres(databaseUrl);
  const db = drizzle(client);

  try {
    console.log('Starting cleanup of all user data...');
    
    // Delete in order of dependencies
    console.log('Deleting setup validation logs...');
    await db.delete(setupValidationLogs);
    
    console.log('Deleting user setup requirements...');
    await db.delete(userSetupRequirements);
    
    console.log('Deleting user API keys...');
    await db.delete(userApiKeys);
    
    console.log('Deleting AI actions...');
    await db.delete(aiActions);
    
    console.log('Deleting incident logs...');
    await db.delete(incidentLogs);
    
    console.log('Deleting incidents...');
    await db.delete(incidents);
    
    console.log('Deleting integrations...');
    await db.delete(integrations);
    
    console.log('Deleting activity logs...');
    await db.delete(activityLogs);
    
    console.log('Deleting all users...');
    const result = await db.delete(users);
    
    console.log('✅ Successfully deleted all user data from the database');
    
  } catch (error) {
    console.error('❌ Error cleaning up users:', error);
    process.exit(1);
  } finally {
    await client.end();
  }
}

// Run the cleanup
cleanupAllUsers();