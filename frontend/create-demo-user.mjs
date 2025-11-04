import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });

const connectionString = process.env.POSTGRES_URL;
if (!connectionString) {
  throw new Error('POSTGRES_URL environment variable is not set');
}

const client = postgres(connectionString);
const db = drizzle(client);

async function createDemoUser() {
  try {
    const email = 'admin@oncall.ai';
    const password = 'AdminPass123!';
    const name = 'Admin User';

    // Check if user already exists
    const existingUser = await client`
      SELECT * FROM users WHERE email = ${email} LIMIT 1
    `;

    if (existingUser.length > 0) {
      console.log('Demo user already exists');
      await client.end();
      return;
    }

    // Hash the password
    const passwordHash = await bcrypt.hash(password, 10);

    // Create the user
    await client`
      INSERT INTO users (email, name, password_hash, role, is_setup_complete, created_at, updated_at)
      VALUES (${email}, ${name}, ${passwordHash}, 'admin', true, NOW(), NOW())
    `;

    console.log('✅ Demo user created successfully');
    console.log('Email:', email);
    console.log('Password:', password);

    await client.end();
  } catch (error) {
    console.error('Error creating demo user:', error);
    await client.end();
    process.exit(1);
  }
}

createDemoUser();
