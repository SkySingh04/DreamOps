import { NextRequest, NextResponse } from 'next/server';
import { getRecentAiActions } from '@/lib/db/dashboard-queries';

// Public endpoint for recent AI actions - no auth required
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '10');

    const aiActions = await getRecentAiActions(limit);
    
    return NextResponse.json(aiActions);
  } catch (error) {
    console.error('Error fetching recent AI actions:', error);
    return NextResponse.json(
      { error: 'Failed to fetch recent AI actions' },
      { status: 500 }
    );
  }
}