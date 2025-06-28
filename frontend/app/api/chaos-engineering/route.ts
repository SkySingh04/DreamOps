import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { service } = body;

    // Simulate chaos engineering - just return success for demo
    return NextResponse.json({
      success: true,
      message: `Chaos deployed for ${service || 'all services'}`,
      service: service || 'all',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Chaos Engineering API',
    description: 'POST to this endpoint to trigger infrastructure chaos'
  });
}