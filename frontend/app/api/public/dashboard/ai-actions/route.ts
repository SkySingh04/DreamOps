import { NextRequest, NextResponse } from 'next/server';

// Public endpoint for recent AI actions - fetches from backend API
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '10');
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

    const response = await fetch(`${backendUrl}/api/v1/agent/action-history/?limit=${limit}`, {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    });

    if (!response.ok) {
      console.error('Failed to fetch AI actions from backend:', response.status);
      return NextResponse.json([]);
    }

    const data = await response.json();
    const actions = (data.actions || []).map((action: any, index: number) => ({
      id: action.id || index + 1,
      action: action.action_type || action.action || 'Unknown Action',
      description: action.description || action.details || null,
      createdAt: action.timestamp || action.created_at || new Date().toISOString(),
      incidentId: action.incident_id || null,
    }));

    return NextResponse.json(actions);
  } catch (error) {
    console.error('Error fetching recent AI actions:', error);
    return NextResponse.json([]);
  }
}