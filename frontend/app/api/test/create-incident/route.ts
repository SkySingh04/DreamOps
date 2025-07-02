import { NextRequest, NextResponse } from 'next/server';
import { createIncident, recordAiAction } from '@/lib/db/dashboard-queries';

export async function POST(request: NextRequest) {
  try {
    console.log('Creating test incident...');
    
    const incident = await createIncident({
      userId: 1, // Test user ID
      title: `Test Incident ${new Date().toLocaleTimeString()}`,
      description: 'This is a test incident created via API',
      severity: 'medium',
      source: 'test',
      sourceId: `TEST-${Date.now()}`,
      metadata: JSON.stringify({ 
        test: true, 
        timestamp: new Date().toISOString() 
      }),
    });

    if (incident) {
      // Also record an AI action
      await recordAiAction({
        userId: 1, // Test user ID
        action: 'investigate',
        description: `Investigating test incident: ${incident.title}`,
        incidentId: incident.id,
        status: 'completed',
      });

      console.log('Test incident created:', incident);
      
      return NextResponse.json({ 
        success: true, 
        incident,
        message: 'Test incident created successfully' 
      });
    } else {
      return NextResponse.json(
        { error: 'Failed to create test incident' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Error creating test incident:', error);
    return NextResponse.json(
      { error: 'Failed to create test incident', details: error },
      { status: 500 }
    );
  }
}