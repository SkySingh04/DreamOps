import { NextRequest, NextResponse } from 'next/server';
import { getDashboardMetrics } from '@/lib/db/dashboard-queries';
import { db } from '@/lib/db/drizzle';
import { teams } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

// Public endpoint for dashboard metrics - no auth required
export async function GET(request: NextRequest) {
  try {
    // Get default team
    const defaultTeam = await db.select().from(teams).where(eq(teams.name, 'Default Team')).limit(1);
    
    let teamId: number;
    if (defaultTeam.length === 0) {
      // Create default team if not exists
      const newTeam = await db.insert(teams).values({
        name: 'Default Team',
        subscriptionStatus: 'trial',
      }).returning();
      teamId = newTeam[0].id;
    } else {
      teamId = defaultTeam[0].id;
    }

    const metrics = await getDashboardMetrics(teamId);
    
    return NextResponse.json(metrics);
  } catch (error) {
    console.error('Error fetching dashboard metrics:', error);
    return NextResponse.json(
      { error: 'Failed to fetch dashboard metrics' },
      { status: 500 }
    );
  }
}