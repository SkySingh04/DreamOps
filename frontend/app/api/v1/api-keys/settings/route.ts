import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { apiKeys, teamMembers } from '@/lib/db/schema';
import { getUser } from '@/lib/db/queries';
import { eq, and } from 'drizzle-orm';

// Legacy function - in new user-based model, we use userId directly
async function getUserTeamId(userId: number): Promise<number | null> {
  // In the new user-based model, we can just return the userId as the "team" ID
  // since each user is now their own team/account
  return userId;
}

// GET /api/v1/api-keys/settings - Get API key settings
export async function GET(request: NextRequest) {
  try {
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const teamId = await getUserTeamId(user.id);
    if (!teamId) {
      return NextResponse.json({ error: 'No team found' }, { status: 400 });
    }

    const db = await getDb();

    // Get all keys for the user
    const keys = await db
      .select({
        id: apiKeys.id,
        isPrimary: apiKeys.isPrimary,
        status: apiKeys.status,
      })
      .from(apiKeys)
      .where(eq(apiKeys.userId, user.id));

    if (keys.length === 0) {
      return NextResponse.json({ error: 'No API keys configured' }, { status: 404 });
    }

    const primaryKey = keys.find(k => k.isPrimary);
    const activeKeys = keys.filter(k => k.status === 'active');
    const fallbackKeys = keys.filter(k => !k.isPrimary && k.status === 'active');

    const settings = {
      active_key_id: primaryKey?.id?.toString() || '',
      fallback_key_ids: fallbackKeys.map(k => k.id.toString()),
      auto_fallback_enabled: true,
      max_retries_before_fallback: 3,
    };

    return NextResponse.json(settings);
  } catch (error) {
    console.error('Error fetching API key settings:', error);
    return NextResponse.json(
      { error: 'Failed to fetch settings' },
      { status: 500 }
    );
  }
}