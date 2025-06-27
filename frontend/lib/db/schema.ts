import {
  pgTable,
  serial,
  varchar,
  text,
  timestamp,
  integer,
  boolean,
  jsonb,
  uuid,
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 100 }),
  email: varchar('email', { length: 255 }).notNull().unique(),
  passwordHash: text('password_hash').notNull(),
  role: varchar('role', { length: 20 }).notNull().default('member'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
  deletedAt: timestamp('deleted_at'),
});

export const teams = pgTable('teams', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 100 }).notNull(),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
  stripeCustomerId: text('stripe_customer_id').unique(),
  stripeSubscriptionId: text('stripe_subscription_id').unique(),
  stripeProductId: text('stripe_product_id'),
  planName: varchar('plan_name', { length: 50 }),
  subscriptionStatus: varchar('subscription_status', { length: 20 }),
});

export const teamMembers = pgTable('team_members', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  role: varchar('role', { length: 50 }).notNull(),
  joinedAt: timestamp('joined_at').notNull().defaultNow(),
});

export const activityLogs = pgTable('activity_logs', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  userId: integer('user_id').references(() => users.id),
  action: text('action').notNull(),
  timestamp: timestamp('timestamp').notNull().defaultNow(),
  ipAddress: varchar('ip_address', { length: 45 }),
});

export const invitations = pgTable('invitations', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  email: varchar('email', { length: 255 }).notNull(),
  role: varchar('role', { length: 50 }).notNull(),
  invitedBy: integer('invited_by')
    .notNull()
    .references(() => users.id),
  invitedAt: timestamp('invited_at').notNull().defaultNow(),
  status: varchar('status', { length: 20 }).notNull().default('pending'),
});

export const incidents = pgTable('incidents', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  title: varchar('title', { length: 255 }).notNull(),
  description: text('description'),
  severity: varchar('severity', { length: 20 }).notNull(), // critical, high, medium, low
  status: varchar('status', { length: 20 }).notNull().default('open'), // open, investigating, resolved, closed
  source: varchar('source', { length: 50 }).notNull(), // pagerduty, kubernetes, manual, etc.
  sourceId: varchar('source_id', { length: 255 }), // external system ID
  assignedTo: integer('assigned_to').references(() => users.id),
  resolvedBy: integer('resolved_by').references(() => users.id),
  resolvedAt: timestamp('resolved_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
  metadata: text('metadata'), // JSON string for additional data
});

export const incidentLogs = pgTable('incident_logs', {
  id: serial('id').primaryKey(),
  incidentId: integer('incident_id')
    .notNull()
    .references(() => incidents.id),
  action: varchar('action', { length: 100 }).notNull(), // created, status_changed, assigned, resolved, etc.
  description: text('description'),
  performedBy: integer('performed_by').references(() => users.id), // null for AI actions
  performedByAi: varchar('performed_by_ai', { length: 50 }), // AI agent name
  createdAt: timestamp('created_at').notNull().defaultNow(),
  metadata: text('metadata'), // JSON string for additional data
});

export const metrics = pgTable('metrics', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  metricType: varchar('metric_type', { length: 50 }).notNull(), // response_time, health_score, incident_count, etc.
  value: text('value').notNull(), // storing as text to handle different value types
  timestamp: timestamp('timestamp').notNull().defaultNow(),
  metadata: text('metadata'), // JSON string for additional data
});

export const aiActions = pgTable('ai_actions', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  incidentId: integer('incident_id').references(() => incidents.id),
  action: varchar('action', { length: 100 }).notNull(),
  description: text('description'),
  status: varchar('status', { length: 20 }).notNull().default('completed'), // pending, completed, failed
  aiAgent: varchar('ai_agent', { length: 50 }).notNull().default('oncall-agent'),
  approvedBy: integer('approved_by').references(() => users.id),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  metadata: text('metadata'), // JSON string for additional data
});

export const teamIntegrations = pgTable('team_integrations', {
  id: uuid('id').primaryKey().defaultRandom(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  integrationType: varchar('integration_type', { length: 50 }).notNull(), // 'pagerduty', 'kubernetes', 'github', 'notion', 'grafana'
  config: jsonb('config').notNull(), // Encrypted configuration data
  isEnabled: boolean('is_enabled').notNull().default(true),
  isRequired: boolean('is_required').notNull().default(false),
  lastTestAt: timestamp('last_test_at'),
  lastTestStatus: varchar('last_test_status', { length: 20 }), // 'success', 'failed', 'pending'
  lastTestError: text('last_test_error'),
  createdBy: integer('created_by')
    .notNull()
    .references(() => users.id),
  updatedBy: integer('updated_by')
    .notNull()
    .references(() => users.id),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
});

export const apiKeys = pgTable('api_keys', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  provider: varchar('provider', { length: 20 }).notNull(),
  name: varchar('name', { length: 100 }).notNull(),
  keyMasked: varchar('key_masked', { length: 20 }).notNull(),
  keyHash: text('key_hash').notNull(),
  isPrimary: boolean('is_primary').notNull().default(false),
  status: varchar('status', { length: 20 }).notNull().default('active'),
  errorCount: integer('error_count').notNull().default(0),
  lastError: text('last_error'),
  lastUsedAt: timestamp('last_used_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
});

export const integrationAuditLogs = pgTable('integration_audit_logs', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  integrationId: uuid('integration_id')
    .notNull()
    .references(() => teamIntegrations.id),
  action: varchar('action', { length: 50 }).notNull(), // 'created', 'updated', 'tested', 'enabled', 'disabled', 'deleted'
  performedBy: integer('performed_by')
    .notNull()
    .references(() => users.id),
  previousConfig: jsonb('previous_config'), // Encrypted previous configuration
  newConfig: jsonb('new_config'), // Encrypted new configuration
  result: varchar('result', { length: 20 }), // 'success', 'failed'
  errorMessage: text('error_message'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  metadata: jsonb('metadata'), // Additional audit data
});

export const apiKeys = pgTable('api_keys', {
  id: serial('id').primaryKey(),
  teamId: integer('team_id')
    .notNull()
    .references(() => teams.id),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  provider: varchar('provider', { length: 20 }).notNull(),
  name: varchar('name', { length: 100 }).notNull(),
  keyMasked: varchar('key_masked', { length: 20 }).notNull(),
  keyHash: text('key_hash').notNull(),
  isPrimary: boolean('is_primary').notNull().default(false),
  status: varchar('status', { length: 20 }).notNull().default('active'),
  errorCount: integer('error_count').notNull().default(0),
  lastError: text('last_error'),
  lastUsedAt: timestamp('last_used_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
});

export const teamsRelations = relations(teams, ({ many }) => ({
  teamMembers: many(teamMembers),
  activityLogs: many(activityLogs),
  invitations: many(invitations),
  incidents: many(incidents),
  metrics: many(metrics),
  aiActions: many(aiActions),
  integrations: many(teamIntegrations),
  integrationAuditLogs: many(integrationAuditLogs),
  apiKeys: many(apiKeys),
}));

export const usersRelations = relations(users, ({ many }) => ({
  teamMembers: many(teamMembers),
  invitationsSent: many(invitations),
  assignedIncidents: many(incidents, { relationName: 'assignedIncidents' }),
  resolvedIncidents: many(incidents, { relationName: 'resolvedIncidents' }),
  incidentLogs: many(incidentLogs),
  approvedAiActions: many(aiActions),
  createdIntegrations: many(teamIntegrations, { relationName: 'createdIntegrations' }),
  updatedIntegrations: many(teamIntegrations, { relationName: 'updatedIntegrations' }),
  integrationAuditLogs: many(integrationAuditLogs),
  apiKeys: many(apiKeys),
}));

export const invitationsRelations = relations(invitations, ({ one }) => ({
  team: one(teams, {
    fields: [invitations.teamId],
    references: [teams.id],
  }),
  invitedBy: one(users, {
    fields: [invitations.invitedBy],
    references: [users.id],
  }),
}));

export const teamMembersRelations = relations(teamMembers, ({ one }) => ({
  user: one(users, {
    fields: [teamMembers.userId],
    references: [users.id],
  }),
  team: one(teams, {
    fields: [teamMembers.teamId],
    references: [teams.id],
  }),
}));

export const activityLogsRelations = relations(activityLogs, ({ one }) => ({
  team: one(teams, {
    fields: [activityLogs.teamId],
    references: [teams.id],
  }),
  user: one(users, {
    fields: [activityLogs.userId],
    references: [users.id],
  }),
}));

export const incidentsRelations = relations(incidents, ({ one, many }) => ({
  team: one(teams, {
    fields: [incidents.teamId],
    references: [teams.id],
  }),
  assignedTo: one(users, {
    fields: [incidents.assignedTo],
    references: [users.id],
    relationName: 'assignedIncidents',
  }),
  resolvedBy: one(users, {
    fields: [incidents.resolvedBy],
    references: [users.id],
    relationName: 'resolvedIncidents',
  }),
  logs: many(incidentLogs),
  aiActions: many(aiActions),
}));

export const incidentLogsRelations = relations(incidentLogs, ({ one }) => ({
  incident: one(incidents, {
    fields: [incidentLogs.incidentId],
    references: [incidents.id],
  }),
  performedBy: one(users, {
    fields: [incidentLogs.performedBy],
    references: [users.id],
  }),
}));

export const metricsRelations = relations(metrics, ({ one }) => ({
  team: one(teams, {
    fields: [metrics.teamId],
    references: [teams.id],
  }),
}));

export const aiActionsRelations = relations(aiActions, ({ one }) => ({
  team: one(teams, {
    fields: [aiActions.teamId],
    references: [teams.id],
  }),
  incident: one(incidents, {
    fields: [aiActions.incidentId],
    references: [incidents.id],
  }),
  approvedBy: one(users, {
    fields: [aiActions.approvedBy],
    references: [users.id],
  }),
}));

export const teamIntegrationsRelations = relations(teamIntegrations, ({ one, many }) => ({
  team: one(teams, {
    fields: [teamIntegrations.teamId],
    references: [teams.id],
  }),
  createdBy: one(users, {
    fields: [teamIntegrations.createdBy],
    references: [users.id],
    relationName: 'createdIntegrations',
  }),
  updatedBy: one(users, {
    fields: [teamIntegrations.updatedBy],
    references: [users.id],
    relationName: 'updatedIntegrations',
  }),
  auditLogs: many(integrationAuditLogs),
}));

export const apiKeysRelations = relations(apiKeys, ({ one }) => ({
  team: one(teams, {
    fields: [apiKeys.teamId],
    references: [teams.id],
  }),
  user: one(users, {
    fields: [apiKeys.userId],
    references: [users.id],
  }),
}));

export const integrationAuditLogsRelations = relations(integrationAuditLogs, ({ one }) => ({
  team: one(teams, {
    fields: [integrationAuditLogs.teamId],
    references: [teams.id],
  }),
  integration: one(teamIntegrations, {
    fields: [integrationAuditLogs.integrationId],
    references: [teamIntegrations.id],
  }),
  performedBy: one(users, {
    fields: [integrationAuditLogs.performedBy],
    references: [users.id],
  }),
}));

export const apiKeysRelations = relations(apiKeys, ({ one }) => ({
  team: one(teams, {
    fields: [apiKeys.teamId],
    references: [teams.id],
  }),
  user: one(users, {
    fields: [apiKeys.userId],
    references: [users.id],
  }),
}));

export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type Team = typeof teams.$inferSelect;
export type NewTeam = typeof teams.$inferInsert;
export type TeamMember = typeof teamMembers.$inferSelect;
export type NewTeamMember = typeof teamMembers.$inferInsert;
export type ActivityLog = typeof activityLogs.$inferSelect;
export type NewActivityLog = typeof activityLogs.$inferInsert;
export type Invitation = typeof invitations.$inferSelect;
export type NewInvitation = typeof invitations.$inferInsert;
export type Incident = typeof incidents.$inferSelect;
export type NewIncident = typeof incidents.$inferInsert;
export type IncidentLog = typeof incidentLogs.$inferSelect;
export type NewIncidentLog = typeof incidentLogs.$inferInsert;
export type Metric = typeof metrics.$inferSelect;
export type NewMetric = typeof metrics.$inferInsert;
export type AiAction = typeof aiActions.$inferSelect;
export type NewAiAction = typeof aiActions.$inferInsert;
export type TeamIntegration = typeof teamIntegrations.$inferSelect;
export type NewTeamIntegration = typeof teamIntegrations.$inferInsert;
export type IntegrationAuditLog = typeof integrationAuditLogs.$inferSelect;
export type NewIntegrationAuditLog = typeof integrationAuditLogs.$inferInsert;
export type APIKey = typeof apiKeys.$inferSelect;
export type NewAPIKey = typeof apiKeys.$inferInsert;
export type TeamDataWithMembers = Team & {
  teamMembers: (TeamMember & {
    user: Pick<User, 'id' | 'name' | 'email'>;
  })[];
};

export enum ActivityType {
  SIGN_UP = 'SIGN_UP',
  SIGN_IN = 'SIGN_IN',
  SIGN_OUT = 'SIGN_OUT',
  UPDATE_PASSWORD = 'UPDATE_PASSWORD',
  DELETE_ACCOUNT = 'DELETE_ACCOUNT',
  UPDATE_ACCOUNT = 'UPDATE_ACCOUNT',
  CREATE_TEAM = 'CREATE_TEAM',
  REMOVE_TEAM_MEMBER = 'REMOVE_TEAM_MEMBER',
  INVITE_TEAM_MEMBER = 'INVITE_TEAM_MEMBER',
  ACCEPT_INVITATION = 'ACCEPT_INVITATION',
}

export enum IntegrationType {
  PAGERDUTY = 'pagerduty',
  KUBERNETES = 'kubernetes',
  GITHUB = 'github',
  NOTION = 'notion',
  GRAFANA = 'grafana',
  DATADOG = 'datadog',
}

export enum IntegrationTestStatus {
  SUCCESS = 'success',
  FAILED = 'failed',
  PENDING = 'pending',
}

export enum IntegrationAuditAction {
  CREATED = 'created',
  UPDATED = 'updated',
  TESTED = 'tested',
  ENABLED = 'enabled',
  DISABLED = 'disabled',
  DELETED = 'deleted',
}
