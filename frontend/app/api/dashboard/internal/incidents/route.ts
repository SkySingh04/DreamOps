import { NextRequest, NextResponse } from 'next/server';
import { createIncident } from '@/lib/db/dashboard-queries';
import { getDb } from '@/lib/db';
import { teams } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

// Internal API endpoint for backend agent - no auth required
export async function POST(request: NextRequest) {
  try {
    const db = await getDb();
    // Check for internal API key or specific header
    const internalKey = request.headers.get('x-internal-api-key');
    if (internalKey !== 'oncall-agent-internal') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { title, description, severity, source, sourceId, metadata, teamName = 'Default Team' } = body;

    if (!title || !severity || !source) {
      return NextResponse.json(
        { error: 'Missing required fields: title, severity, source' },
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
        subscriptionStatus: 'trial',
      }).returning();
      teamId = newTeam[0].id;
    } else {
      teamId = team[0].id;
    }

    const incident = await createIncident(teamId, {
      title,
      description,
      severity,
      source,
      sourceId,
      metadata: metadata ? JSON.stringify(metadata) : undefined,
    });

    if (!incident) {
      return NextResponse.json(
        { error: 'Failed to create incident' },
        { status: 500 }
      );
    }

    return NextResponse.json(incident, { status: 201 });
  } catch (error) {
    console.error('Error creating incident from backend:', error);
    return NextResponse.json(
      { error: 'Failed to create incident' },
      { status: 500 }
    );
  }
}