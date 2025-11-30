import { NextRequest, NextResponse } from 'next/server';

// Public endpoint for recent incidents - fetches from backend API
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '10');
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

    const response = await fetch(`${backendUrl}/api/v1/incidents/?page_size=${limit}`, {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    });

    if (!response.ok) {
      console.error('Failed to fetch incidents from backend:', response.status);
      return NextResponse.json([]);
    }

    const data = await response.json();
    const incidents = (data.incidents || []).map((incident: any) => ({
      id: incident.id,
      title: incident.title,
      severity: incident.severity,
      status: incident.status,
      createdAt: incident.created_at,
    }));

    return NextResponse.json(incidents);
  } catch (error) {
    console.error('Error fetching recent incidents:', error);
    return NextResponse.json([]);
  }
}