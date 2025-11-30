import { NextRequest, NextResponse } from 'next/server';

// Public endpoint for dashboard metrics - fetches from backend API
export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

    // Fetch incidents from backend to calculate metrics (use trailing slash for FastAPI)
    const incidentsResponse = await fetch(`${backendUrl}/api/v1/incidents/?page_size=100`, {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    });

    if (!incidentsResponse.ok) {
      console.error('Failed to fetch incidents from backend:', incidentsResponse.status);
      // Return default metrics if backend is unavailable
      return NextResponse.json({
        activeIncidents: 0,
        resolvedToday: 0,
        avgResponseTime: '0 min',
        healthScore: 95,
        aiAgentStatus: 'online',
      });
    }

    const incidentsData = await incidentsResponse.json();
    const incidents = incidentsData.incidents || [];

    // Calculate metrics from incidents
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const activeIncidents = incidents.filter((i: any) =>
      i.status === 'triggered' || i.status === 'acknowledged'
    ).length;

    const resolvedToday = incidents.filter((i: any) => {
      if (i.status !== 'resolved' || !i.resolved_at) return false;
      const resolvedDate = new Date(i.resolved_at);
      return resolvedDate >= today;
    }).length;

    // Calculate average response time for resolved incidents
    let avgResponseTime = '0 min';
    const resolvedIncidents = incidents.filter((i: any) => i.resolved_at && i.created_at);
    if (resolvedIncidents.length > 0) {
      const totalMinutes = resolvedIncidents.reduce((sum: number, i: any) => {
        const created = new Date(i.created_at).getTime();
        const resolved = new Date(i.resolved_at).getTime();
        return sum + (resolved - created) / (1000 * 60);
      }, 0);
      const avg = Math.round(totalMinutes / resolvedIncidents.length);
      avgResponseTime = avg < 60 ? `${avg} min` : `${Math.round(avg / 60)}h ${avg % 60}m`;
    }

    return NextResponse.json({
      activeIncidents,
      resolvedToday,
      avgResponseTime,
      healthScore: activeIncidents === 0 ? 100 : Math.max(50, 100 - (activeIncidents * 10)),
      aiAgentStatus: 'online' as const,
    });
  } catch (error) {
    console.error('Error fetching dashboard metrics:', error);
    // Return default metrics on error
    return NextResponse.json({
      activeIncidents: 0,
      resolvedToday: 0,
      avgResponseTime: '0 min',
      healthScore: 95,
      aiAgentStatus: 'online',
    });
  }
}