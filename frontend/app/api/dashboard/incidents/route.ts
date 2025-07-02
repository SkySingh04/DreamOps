import { NextRequest, NextResponse } from 'next/server';
import { getUser } from '@/lib/db/queries';
import { getRecentIncidents, createIncident } from '@/lib/db/dashboard-queries';

// Force dynamic rendering to prevent build-time database access
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

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

export async function POST(request: NextRequest) {
  try {
    const user = await getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { title, description, severity, source, sourceId, metadata } = body;

    if (!title || !severity || !source) {
      return NextResponse.json(
        { error: 'Missing required fields: title, severity, source' },
        { status: 400 }
      );
    }

    const incident = await createIncident({
      userId: user.id,
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
    console.error('Error creating incident:', error);
    return NextResponse.json(
      { error: 'Failed to create incident' },
      { status: 500 }
    );
  }
}