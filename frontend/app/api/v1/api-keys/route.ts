import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { apiKeys, users, teamMembers } from '@/lib/db/schema';
import { getUser } from '@/lib/db/queries';
import { eq, and, desc } from 'drizzle-orm';
import { createHash } from 'crypto';

interface APIKeyCreate {
  provider: 'anthropic' | 'openai';
  api_key: string;
  name: string;
  is_primary?: boolean;
}

function maskApiKey(key: string): string {
  if (key.length < 8) return key;
  return `${key.slice(0, 3)}...${key.slice(-4)}`;
}

function hashApiKey(key: string): string {
  return createHash('sha256').update(key).digest('hex');
}

function validateApiKey(provider: string, key: string): boolean {
  if (provider === 'anthropic') {
    return key.startsWith('sk-ant-') && key.length > 20;
  } else if (provider === 'openai') {
    return key.startsWith('sk-') && key.length > 20;
  }
  return false;
}

// Legacy function - in new user-based model, we use userId directly
async function getUserTeamId(userId: number): Promise<number | null> {
  // In the new user-based model, we can just return the userId as the "team" ID
  // since each user is now their own team/account
  return userId;
}

// GET /api/v1/api-keys - List all API keys for the user's team
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
    const keys = await db
      .select({
        id: apiKeys.id,
        provider: apiKeys.provider,
        name: apiKeys.name,
        api_key_masked: apiKeys.keyMasked,
        is_primary: apiKeys.isPrimary,
        status: apiKeys.status,
        error_count: apiKeys.errorCount,
        last_error: apiKeys.lastError,
        last_used_at: apiKeys.lastUsedAt,
        created_at: apiKeys.createdAt,
        updated_at: apiKeys.updatedAt,
      })
      .from(apiKeys)
      .where(eq(apiKeys.userId, user.id))
      .orderBy(desc(apiKeys.isPrimary), desc(apiKeys.createdAt));

    return NextResponse.json(keys);
  } catch (error) {
    console.error('Error fetching API keys:', error);
    return NextResponse.json(
      { error: 'Failed to fetch API keys' },
      { status: 500 }
    );
  }
}

// POST /api/v1/api-keys - Create a new API key
export async function POST(request: NextRequest) {
  try {
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const teamId = await getUserTeamId(user.id);
    if (!teamId) {
      return NextResponse.json({ error: 'No team found' }, { status: 400 });
    }

    const body: APIKeyCreate = await request.json();
    const { provider, api_key, name, is_primary = false } = body;

    // Validate input
    if (!provider || !api_key || !name) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    if (!validateApiKey(provider, api_key)) {
      return NextResponse.json(
        { error: 'Invalid API key format' },
        { status: 400 }
      );
    }

    const db = await getDb();

    // Check if this is the first key for the user
    const existingKeys = await db
      .select({ id: apiKeys.id })
      .from(apiKeys)
      .where(eq(apiKeys.userId, user.id));

    const isFirstKey = existingKeys.length === 0;
    const shouldBePrimary = isFirstKey || is_primary;

    // If setting as primary, unset other primary keys for this user
    if (shouldBePrimary) {
      await db
        .update(apiKeys)
        .set({ isPrimary: false })
        .where(eq(apiKeys.userId, user.id));
    }

    // Create the new API key
    const [newKey] = await db
      .insert(apiKeys)
      .values({
        userId: user.id,
        provider,
        name,
        keyMasked: maskApiKey(api_key),
        keyHash: hashApiKey(api_key),
        isPrimary: shouldBePrimary,
        status: 'active',
        errorCount: 0,
      })
      .returning({
        id: apiKeys.id,
        provider: apiKeys.provider,
        name: apiKeys.name,
        api_key_masked: apiKeys.keyMasked,
        is_primary: apiKeys.isPrimary,
        status: apiKeys.status,
        error_count: apiKeys.errorCount,
        last_error: apiKeys.lastError,
        last_used_at: apiKeys.lastUsedAt,
        created_at: apiKeys.createdAt,
        updated_at: apiKeys.updatedAt,
      });

    return NextResponse.json(newKey, { status: 201 });
  } catch (error) {
    console.error('Error creating API key:', error);
    return NextResponse.json(
      { error: 'Failed to create API key' },
      { status: 500 }
    );
  }
}