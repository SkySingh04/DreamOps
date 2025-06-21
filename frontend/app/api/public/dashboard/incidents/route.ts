import { NextRequest, NextResponse } from 'next/server';
import { getRecentIncidents } from '@/lib/db/dashboard-queries';
import { db } from '@/lib/db/drizzle';
import { teams } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

// Public endpoint for recent incidents - no auth required
export async function GET(request: NextRequest) {
  try {
    // Get default team
    const defaultTeam = await db.select().from(teams).where(eq(teams.name, 'Default Team')).limit(1);
    
    let teamId: number;
    if (defaultTeam.length === 0) {
      // Create default team if not exists
      const newTeam = await db.insert(teams).values({
        name: 'Default Team',
        subscription_status: 'trial',
      }).returning();
      teamId = newTeam[0].id;
    } else {
      teamId = defaultTeam[0].id;
    }

    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '10');

    const incidents = await getRecentIncidents(teamId, limit);
    
    return NextResponse.json(incidents);
  } catch (error) {
    console.error('Error fetching recent incidents:', error);
    return NextResponse.json(
      { error: 'Failed to fetch recent incidents' },
      { status: 500 }
    );
  }
}