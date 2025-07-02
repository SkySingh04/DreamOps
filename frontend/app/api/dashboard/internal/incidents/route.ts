import { NextRequest, NextResponse } from 'next/server';
import { createIncident } from '@/lib/db/dashboard-queries';

// Internal API endpoint for backend agent - no auth required
export async function POST(request: NextRequest) {
  try {
    // Check for internal API key or specific header
    const internalKey = request.headers.get('x-internal-api-key');
    if (internalKey !== 'oncall-agent-internal') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { userId, title, description, severity, source, sourceId, metadata } = body;

    if (!title || !severity || !source || !userId) {
      return NextResponse.json(
        { error: 'Missing required fields: userId, title, severity, source' },
        { status: 400 }
      );
    }

    const incident = await createIncident({
      userId,
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