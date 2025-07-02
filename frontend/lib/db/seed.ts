// Seed script for initial user
import { getDb } from './drizzle';
import { users } from './schema';
import { hashPassword } from '@/lib/auth/session-crypto';

async function seed() {
  const email = 'test@test.com';
  const password = 'admin123';
  const passwordHash = await hashPassword(password);

  const db = await getDb();
  const [user] = await db
    .insert(users)
    .values([
      {
        email: email,
        passwordHash: passwordHash,
        role: "owner",
      },
    ])
    .returning();

  console.log('Initial user created.');
  console.log('Email:', email);
  console.log('Password:', password);
  console.log('User ID:', user.id);
}

seed()
  .catch((error) => {
    console.error('Seed process failed:', error);
    process.exit(1);
  })
  .finally(() => {
    console.log('Seed process finished. Exiting...');
    process.exit(0);
  });
