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

async function updatePassword() {
  try {
    const email = 'admin@oncall.ai';
    const password = 'AdminPass123!';

    // Hash the password
    const passwordHash = await bcrypt.hash(password, 10);

    // Update the user password
    const result = await client`
      UPDATE users 
      SET password_hash = ${passwordHash}, 
          is_setup_complete = true,
          updated_at = NOW()
      WHERE email = ${email}
      RETURNING id, email, name
    `;

    if (result.length > 0) {
      console.log('✅ Password updated successfully for:', result[0].email);
      console.log('Email:', email);
      console.log('Password:', password);
    } else {
      console.log('❌ User not found');
    }

    await client.end();
  } catch (error) {
    console.error('Error updating password:', error);
    await client.end();
    process.exit(1);
  }
}

updatePassword();
