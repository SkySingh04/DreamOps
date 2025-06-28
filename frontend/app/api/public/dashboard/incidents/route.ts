import { NextRequest, NextResponse } from 'next/server';
import { getRecentIncidents } from '@/lib/db/dashboard-queries';

// Public endpoint for recent incidents - no auth required
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '10');

    const incidents = await getRecentIncidents(limit);
    
    return NextResponse.json(incidents);
  } catch (error) {
    console.error('Error fetching recent incidents:', error);
    return NextResponse.json(
      { error: 'Failed to fetch recent incidents' },
      { status: 500 }
    );
  }
}