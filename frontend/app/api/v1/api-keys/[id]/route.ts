import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { apiKeys, teamMembers } from '@/lib/db/schema';
import { getUser } from '@/lib/db/queries';
import { eq, and } from 'drizzle-orm';

interface APIKeyUpdate {
  name?: string;
  is_primary?: boolean;
}

// Legacy function - in new user-based model, we use userId directly
async function getUserTeamId(userId: number): Promise<number | null> {
  // In the new user-based model, we can just return the userId as the "team" ID
  // since each user is now their own team/account
  return userId;
}

// GET /api/v1/api-keys/[id] - Get a specific API key
export async function GET(
  request: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  const params = await props.params;
  try {
    const { id } = await params;
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const teamId = await getUserTeamId(user.id);
    if (!teamId) {
      return NextResponse.json({ error: 'No team found' }, { status: 400 });
    }

    const db = await getDb();
    const [key] = await db
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
      .where(
        and(
          eq(apiKeys.id, parseInt(id)),
          eq(apiKeys.userId, user.id)
        )
      )
      .limit(1);

    if (!key) {
      return NextResponse.json({ error: 'API key not found' }, { status: 404 });
    }

    return NextResponse.json(key);
  } catch (error) {
    console.error('Error fetching API key:', error);
    return NextResponse.json(
      { error: 'Failed to fetch API key' },
      { status: 500 }
    );
  }
}

// PUT /api/v1/api-keys/[id] - Update an API key
export async function PUT(
  request: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  const params = await props.params;
  try {
    const { id } = await params;
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const teamId = await getUserTeamId(user.id);
    if (!teamId) {
      return NextResponse.json({ error: 'No team found' }, { status: 400 });
    }

    const body: APIKeyUpdate = await request.json();
    const { name, is_primary } = body;

    const db = await getDb();

    // Check if the key exists and belongs to the team
    const [existingKey] = await db
      .select({ id: apiKeys.id })
      .from(apiKeys)
      .where(
        and(
          eq(apiKeys.id, parseInt(id)),
          eq(apiKeys.userId, user.id)
        )
      )
      .limit(1);

    if (!existingKey) {
      return NextResponse.json({ error: 'API key not found' }, { status: 404 });
    }

    // If setting as primary, unset other primary keys
    if (is_primary) {
      await db
        .update(apiKeys)
        .set({ isPrimary: false })
        .where(eq(apiKeys.userId, user.id));
    }

    // Update the key
    const updateData: any = { updatedAt: new Date() };
    if (name !== undefined) updateData.name = name;
    if (is_primary !== undefined) updateData.isPrimary = is_primary;

    const [updatedKey] = await db
      .update(apiKeys)
      .set(updateData)
      .where(eq(apiKeys.id, parseInt(id)))
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

    return NextResponse.json(updatedKey);
  } catch (error) {
    console.error('Error updating API key:', error);
    return NextResponse.json(
      { error: 'Failed to update API key' },
      { status: 500 }
    );
  }
}

// DELETE /api/v1/api-keys/[id] - Delete an API key
export async function DELETE(
  request: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  const params = await props.params;
  try {
    const { id } = await params;
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const teamId = await getUserTeamId(user.id);
    if (!teamId) {
      return NextResponse.json({ error: 'No team found' }, { status: 400 });
    }

    const db = await getDb();

    // Check if this is the last key
    const allKeys = await db
      .select({ id: apiKeys.id })
      .from(apiKeys)
      .where(eq(apiKeys.userId, user.id));

    if (allKeys.length <= 1) {
      return NextResponse.json(
        { error: 'Cannot delete the last API key' },
        { status: 400 }
      );
    }

    // Check if the key exists and belongs to the team
    const [existingKey] = await db
      .select({ id: apiKeys.id, isPrimary: apiKeys.isPrimary })
      .from(apiKeys)
      .where(
        and(
          eq(apiKeys.id, parseInt(id)),
          eq(apiKeys.userId, user.id)
        )
      )
      .limit(1);

    if (!existingKey) {
      return NextResponse.json({ error: 'API key not found' }, { status: 404 });
    }

    // Delete the key
    await db
      .delete(apiKeys)
      .where(eq(apiKeys.id, parseInt(id)));

    // If we deleted the primary key, make another key primary
    if (existingKey.isPrimary) {
      const [nextKey] = await db
        .select({ id: apiKeys.id })
        .from(apiKeys)
        .where(eq(apiKeys.userId, user.id))
        .limit(1);

      if (nextKey) {
        await db
          .update(apiKeys)
          .set({ isPrimary: true })
          .where(eq(apiKeys.id, nextKey.id));
      }
    }

    return NextResponse.json({ message: 'API key deleted successfully' });
  } catch (error) {
    console.error('Error deleting API key:', error);
    return NextResponse.json(
      { error: 'Failed to delete API key' },
      { status: 500 }
    );
  }
}