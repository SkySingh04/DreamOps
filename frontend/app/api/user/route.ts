import { getUser } from '@/lib/db/queries';
import { cookies } from 'next/headers';
import { getDb } from '@/lib/db/drizzle';
import { users } from '@/lib/db/schema';
import { eq, isNull, and } from 'drizzle-orm';

export async function GET() {
  try {
    // First try session-based auth
    const user = await getUser();
    if (user) {
      return Response.json(user);
    }

    // If no session, check for Firebase token
    const cookieStore = await cookies();
    const firebaseToken = cookieStore.get('firebase-token');
    
    if (!firebaseToken || !firebaseToken.value) {
      return Response.json(null);
    }

    // For now, return a mock user for Firebase-authenticated users
    // In production, you would validate the Firebase token and get the user from the database
    return Response.json({
      id: 1,
      email: 'user@example.com',
      name: 'Firebase User',
      accountTier: 'free'
    });
  } catch (error) {
    console.error('Error in /api/user:', error);
    return Response.json(null);
  }
}
