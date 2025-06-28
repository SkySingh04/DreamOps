import { NextRequest, NextResponse } from 'next/server';
import { recordAiAction } from '@/lib/db/dashboard-queries';

// Internal API endpoint for backend agent - no auth required
export async function POST(request: NextRequest) {
  try {
    // Check for internal API key or specific header
    const internalKey = request.headers.get('x-internal-api-key');
    if (internalKey !== 'oncall-agent-internal') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { action, description, incidentId, status, metadata } = body;

    if (!action || !status) {
      return NextResponse.json(
        { error: 'Missing required fields: action, status' },
        { status: 400 }
      );
    }

    const aiAction = await recordAiAction({
      action,
      description,
      incidentId,
      status,
      metadata: metadata ? JSON.stringify(metadata) : undefined,
    });

    if (!aiAction) {
      return NextResponse.json(
        { error: 'Failed to record AI action' },
        { status: 500 }
      );
    }

    return NextResponse.json(aiAction, { status: 201 });
  } catch (error) {
    console.error('Error recording AI action from backend:', error);
    return NextResponse.json(
      { error: 'Failed to record AI action' },
      { status: 500 }
    );
  }
}