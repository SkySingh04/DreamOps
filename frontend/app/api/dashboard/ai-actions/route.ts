import { NextRequest, NextResponse } from 'next/server';
import { getUser } from '@/lib/db/queries';
import { getUserWithTeam } from '@/lib/db/queries';
import { getRecentAiActions, recordAiAction } from '@/lib/db/dashboard-queries';

export async function GET(request: NextRequest) {
  try {
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userWithTeam = await getUserWithTeam(user.id);
    if (!userWithTeam?.teamId) {
      return NextResponse.json({ error: 'User not part of a team' }, { status: 400 });
    }

    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '10');

    const aiActions = await getRecentAiActions(userWithTeam.teamId, limit);
    
    return NextResponse.json(aiActions);
  } catch (error) {
    console.error('Error fetching recent AI actions:', error);
    return NextResponse.json(
      { error: 'Failed to fetch recent AI actions' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userWithTeam = await getUserWithTeam(user.id);
    if (!userWithTeam?.teamId) {
      return NextResponse.json({ error: 'User not part of a team' }, { status: 400 });
    }

    const body = await request.json();
    const { action, description, incidentId, status, metadata } = body;

    if (!action) {
      return NextResponse.json(
        { error: 'Missing required field: action' },
        { status: 400 }
      );
    }

    await recordAiAction(userWithTeam.teamId, {
      action,
      description,
      incidentId,
      status,
      metadata: metadata ? JSON.stringify(metadata) : undefined,
    });

    return NextResponse.json({ success: true }, { status: 201 });
  } catch (error) {
    console.error('Error recording AI action:', error);
    return NextResponse.json(
      { error: 'Failed to record AI action' },
      { status: 500 }
    );
  }
}