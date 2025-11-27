import { getDb } from './drizzle';
import { eq, desc, sql, and, gte, lt } from 'drizzle-orm';
import { pgTable, serial, varchar, text, timestamp, integer, boolean } from 'drizzle-orm/pg-core';
import {
  incidents,
  metrics,
  aiActions,
  incidentLogs,
  users,
  type Incident,
  type AiAction,
  type Metric
} from './schema';

// Dashboard incidents table - matches backend's dashboard_sync_service schema
const dashboardIncidents = pgTable('dashboard_incidents', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').notNull(),
  title: varchar('title', { length: 255 }).notNull(),
  description: text('description'),
  severity: varchar('severity', { length: 20 }).notNull(),
  status: varchar('status', { length: 20 }).notNull().default('open'),
  source: varchar('source', { length: 50 }).notNull(),
  sourceId: varchar('source_id', { length: 255 }),
  assignedTo: integer('assigned_to'),
  resolvedBy: integer('resolved_by'),
  resolvedAt: timestamp('resolved_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
  metadata: text('metadata'),
});

export interface DashboardMetrics {
  activeIncidents: number;
  resolvedToday: number;
  avgResponseTime: string;
  healthScore: number;
  aiAgentStatus: 'online' | 'offline';
}

export interface RecentIncident {
  id: number;
  title: string;
  severity: string;
  status: string;
  createdAt: Date;
}

export interface RecentAiAction {
  id: number;
  action: string;
  description: string | null;
  createdAt: Date;
  incidentId?: number | null;
}

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  try {
    const db = await getDb();
    // Get active incidents count from dashboard_incidents table
    const activeIncidentsResult = await db
      .select({ count: sql<number>`count(*)` })
      .from(dashboardIncidents)
      .where(
        sql`${dashboardIncidents.status} IN ('open', 'investigating')`
      );

    // Get resolved incidents today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const resolvedTodayResult = await db
      .select({ count: sql<number>`count(*)` })
      .from(dashboardIncidents)
      .where(
        and(
          eq(dashboardIncidents.status, 'resolved'),
          gte(dashboardIncidents.resolvedAt, today),
          lt(dashboardIncidents.resolvedAt, tomorrow)
        )
      );

    // Get latest health score metric
    const healthScoreResult = await db
      .select({ value: metrics.value })
      .from(metrics)
      .where(
        eq(metrics.metricType, 'health_score')
      )
      .orderBy(desc(metrics.timestamp))
      .limit(1);

    // Get latest response time metric
    const responseTimeResult = await db
      .select({ value: metrics.value })
      .from(metrics)
      .where(
        eq(metrics.metricType, 'avg_response_time')
      )
      .orderBy(desc(metrics.timestamp))
      .limit(1);

    // Get AI agent status
    const aiStatusResult = await db
      .select({ value: metrics.value })
      .from(metrics)
      .where(
        eq(metrics.metricType, 'ai_agent_status')
      )
      .orderBy(desc(metrics.timestamp))
      .limit(1);

    return {
      activeIncidents: activeIncidentsResult[0]?.count || 0,
      resolvedToday: resolvedTodayResult[0]?.count || 0,
      avgResponseTime: responseTimeResult[0]?.value || '0 min',
      healthScore: healthScoreResult[0] ? parseInt(healthScoreResult[0].value) : 95,
      aiAgentStatus: (aiStatusResult[0]?.value as 'online' | 'offline') || 'online',
    };
  } catch (error) {
    console.error('Error fetching dashboard metrics:', error);
    // Return default values on error
    return {
      activeIncidents: 0,
      resolvedToday: 0,
      avgResponseTime: '0 min',
      healthScore: 95,
      aiAgentStatus: 'online',
    };
  }
}

export async function getRecentIncidents(limit: number = 10): Promise<RecentIncident[]> {
  try {
    const db = await getDb();
    // Query from dashboard_incidents table populated by backend
    const result = await db
      .select({
        id: dashboardIncidents.id,
        title: dashboardIncidents.title,
        severity: dashboardIncidents.severity,
        status: dashboardIncidents.status,
        createdAt: dashboardIncidents.createdAt,
      })
      .from(dashboardIncidents)
      .orderBy(desc(dashboardIncidents.createdAt))
      .limit(limit);

    return result;
  } catch (error) {
    console.error('Error fetching recent incidents:', error);
    return [];
  }
}

export async function getRecentAiActions(limit: number = 10): Promise<RecentAiAction[]> {
  try {
    const db = await getDb();
    const result = await db
      .select({
        id: aiActions.id,
        action: aiActions.action,
        description: aiActions.description,
        createdAt: aiActions.createdAt,
        incidentId: aiActions.incidentId,
      })
      .from(aiActions)
      .orderBy(desc(aiActions.createdAt))
      .limit(limit);

    return result;
  } catch (error) {
    console.error('Error fetching recent AI actions:', error);
    return [];
  }
}

export async function createIncident(incidentData: {
  userId: number;
  title: string;
  description?: string;
  severity: string;
  source: string;
  sourceId?: string;
  metadata?: string;
}): Promise<Incident | null> {
  try {
    const db = await getDb();
    const [newIncident] = await db
      .insert(incidents)
      .values({
        userId: incidentData.userId,
        title: incidentData.title,
        description: incidentData.description,
        severity: incidentData.severity,
        source: incidentData.source,
        sourceId: incidentData.sourceId,
        metadata: incidentData.metadata,
      })
      .returning();

    // Log the incident creation
    if (newIncident) {
      await db.insert(incidentLogs).values({
        incidentId: newIncident.id,
        action: 'created',
        description: `Incident created from ${incidentData.source}`,
        performedByAi: 'oncall-agent',
      });
    }

    return newIncident;
  } catch (error) {
    console.error('Error creating incident:', error);
    return null;
  }
}

export async function recordMetric(userId: number, metricType: string, value: string, metadata?: string): Promise<void> {
  try {
    const db = await getDb();
    await db.insert(metrics).values({
      userId,
      metricType,
      value,
      metadata,
    });
  } catch (error) {
    console.error('Error recording metric:', error);
  }
}

export async function recordAiAction(actionData: {
  userId: number;
  action: string;
  description?: string;
  incidentId?: number;
  status?: string;
  metadata?: string;
}): Promise<AiAction | null> {
  try {
    const db = await getDb();
    const [newAction] = await db.insert(aiActions).values({
      userId: actionData.userId,
      action: actionData.action,
      description: actionData.description,
      incidentId: actionData.incidentId,
      status: actionData.status || 'completed',
      metadata: actionData.metadata,
    }).returning();
    
    return newAction;
  } catch (error) {
    console.error('Error recording AI action:', error);
    return null;
  }
}