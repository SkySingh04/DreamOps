import { NextRequest, NextResponse } from 'next/server';
import { recordAiAction } from '@/lib/db/dashboard-queries';
import { db } from '@/lib/db';
import { teams } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

// Internal API endpoint for backend agent - no auth required
export async function POST(request: NextRequest) {
  try {
    // Check for internal API key or specific header
    const internalKey = request.headers.get('x-internal-api-key');
    if (internalKey !== 'oncall-agent-internal') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { action, description, incidentId, status, metadata, teamName = 'Default Team' } = body;

    if (!action || !status) {
      return NextResponse.json(
        { error: 'Missing required fields: action, status' },
        { status: 400 }
      );
    }

    // Get or create default team
    let team = await db.select().from(teams).where(eq(teams.name, teamName)).limit(1);
    
    let teamId: number;
    if (team.length === 0) {
      // Create default team if not exists
      const newTeam = await db.insert(teams).values({
        name: teamName,
        subscription_status: 'trial',
      }).returning();
      teamId = newTeam[0].id;
    } else {
      teamId = team[0].id;
    }

    const aiAction = await recordAiAction(teamId, {
      action,
      description,
      incidentId,
      status,
      metadata: metadata ? JSON.stringify(metadata) : undefined,
    });

    if (!aiAction) {
      return NextResponse.json(
        { error: 'Failed to record AI action' },
        { status: 500 }
      );
    }

    return NextResponse.json(aiAction, { status: 201 });
  } catch (error) {
    console.error('Error recording AI action from backend:', error);
    return NextResponse.json(
      { error: 'Failed to record AI action' },
      { status: 500 }
    );
  }
}