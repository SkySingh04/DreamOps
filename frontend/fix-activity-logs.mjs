import postgres from 'postgres';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });

const connectionString = process.env.POSTGRES_URL;
if (!connectionString) {
  throw new Error('POSTGRES_URL environment variable is not set');
}

const client = postgres(connectionString);

async function fixActivityLogs() {
  try {
    console.log('Altering activity_logs table to make team_id nullable...');
    
    // Make team_id nullable
    await client`
      ALTER TABLE activity_logs 
      ALTER COLUMN team_id DROP NOT NULL
    `;
    
    console.log('✅ Successfully made team_id nullable in activity_logs table');
    
    await client.end();
  } catch (error) {
    console.error('Error altering activity_logs table:', error);
    await client.end();
    process.exit(1);
  }
}

fixActivityLogs();
