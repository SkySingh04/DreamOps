import { NextResponse } from 'next/server';
import { getCurrentUserTeamId } from '@/lib/db/get-user-team';

export async function GET() {
  try {
    const teamId = await getCurrentUserTeamId();
    
    if (!teamId) {
      return NextResponse.json({ error: 'User not found or not part of a team' }, { status: 404 });
    }

    return NextResponse.json({ teamId });
  } catch (error) {
    console.error('Error getting user team:', error);
    return NextResponse.json(
      { error: 'Failed to get user team' },
      { status: 500 }
    );
  }
}