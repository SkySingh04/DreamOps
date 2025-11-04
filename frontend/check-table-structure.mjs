import postgres from 'postgres';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });

const connectionString = process.env.POSTGRES_URL;
const client = postgres(connectionString);

async function checkTable() {
  try {
    console.log('Checking activity_logs table structure...');
    
    const columns = await client`
      SELECT column_name, data_type, is_nullable, column_default
      FROM information_schema.columns
      WHERE table_name = 'activity_logs'
      ORDER BY ordinal_position
    `;
    
    console.log('activity_logs columns:');
    columns.forEach(col => {
      console.log(`  - ${col.column_name}: ${col.data_type}, nullable: ${col.is_nullable}, default: ${col.column_default}`);
    });
    
    await client.end();
  } catch (error) {
    console.error('Error:', error);
    await client.end();
  }
}

checkTable();
