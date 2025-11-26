import { headers } from 'next/headers';
import { getDb } from '@/lib/db/drizzle';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET() {
  try {
    // Get Authentik headers passed by reverse proxy
    const headersList = await headers();

    // Authentik passes user info via these headers
    const username = headersList.get('X-Authentik-Username') || headersList.get('x-authentik-username');
    const email = headersList.get('X-Authentik-Email') || headersList.get('x-authentik-email');
    const name = headersList.get('X-Authentik-Name') || headersList.get('x-authentik-name');
    const groups = headersList.get('X-Authentik-Groups') || headersList.get('x-authentik-groups');

    // If no Authentik headers, user is not authenticated
    if (!email) {
      // For development/testing, return a mock user if no auth headers
      if (process.env.NODE_ENV === 'development' || process.env.ALLOW_MOCK_USER === 'true') {
        return Response.json({
          id: 1,
          email: 'dev@dreamops.local',
          name: 'Dev User',
          accountTier: 'free',
          role: 'admin',
        });
      }
      return Response.json(null);
    }

    // Get database instance
    const db = await getDb();

    // Try to find existing user by email
    let user = await db.query.users.findFirst({
      where: eq(users.email, email),
    });

    // If user doesn't exist, create them (auto-provisioning from Authentik)
    if (!user) {
      const [newUser] = await db.insert(users).values({
        email: email,
        name: name || username || email.split('@')[0],
        role: groups?.includes('admin') ? 'admin' : 'member',
        accountTier: 'free',
        alertsLimit: 3,
        alertsUsed: 0,
      }).returning();
      user = newUser;
    }

    // Return user data for the frontend
    return Response.json({
      id: user.id,
      email: user.email,
      name: user.name,
      accountTier: user.accountTier || 'free',
      role: user.role,
      alertsUsed: user.alertsUsed,
      alertsLimit: user.alertsLimit,
      isSetupComplete: user.isSetupComplete,
    });
  } catch (error) {
    console.error('Error in /api/user:', error);
    return Response.json(null);
  }
}
