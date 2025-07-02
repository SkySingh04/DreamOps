import postgres from 'postgres';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });

const sql = postgres(process.env.POSTGRES_URL);

async function checkTables() {
  try {
    console.log('Checking existing tables in database...\n');
    
    // Query to get all tables in the public schema
    const tables = await sql`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      ORDER BY table_name;
    `;
    
    console.log('Existing tables:');
    tables.forEach(row => {
      console.log(`- ${row.table_name}`);
    });
    
    console.log(`\nTotal tables: ${tables.length}`);
    
    // Check if drizzle migration table exists
    const migrationTable = tables.find(t => t.table_name === '__drizzle_migrations');
    if (migrationTable) {
      console.log('\nDrizzle migrations table found. Checking applied migrations:');
      const migrations = await sql`
        SELECT hash, created_at 
        FROM __drizzle_migrations 
        ORDER BY created_at;
      `;
      migrations.forEach(m => {
        console.log(`- ${m.hash} (applied at: ${m.created_at})`);
      });
    }
    
  } catch (error) {
    console.error('Error checking tables:', error);
  } finally {
    await sql.end();
  }
}

checkTables();