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
  firebaseUid: varchar('firebase_uid', { length: 128 }).unique(),
  name: varchar('name', { length: 100 }),
  email: varchar('email', { length: 255 }).notNull().unique(),
  passwordHash: text('password_hash'),
  role: varchar('role', { length: 20 }).notNull().default('member'),
  llmProvider: varchar('llm_provider', { length: 20 }),
  llmModel: varchar('llm_model', { length: 50 }),
  isSetupComplete: boolean('is_setup_complete').notNull().default(false),
  setupCompletedAt: timestamp('setup_completed_at'),
  lastValidationAt: timestamp('last_validation_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
  deletedAt: timestamp('deleted_at'),
  // Payment and subscription fields (adapted from teams to users)
  stripeCustomerId: text('stripe_customer_id').unique(),
  stripeSubscriptionId: text('stripe_subscription_id').unique(),
  stripeProductId: text('stripe_product_id'),
  planName: varchar('plan_name', { length: 50 }),
  subscriptionStatus: varchar('subscription_status', { length: 20 }),
  accountTier: varchar('account_tier', { length: 20 }).default('free'),
  alertsUsed: integer('alerts_used').default(0),
  alertsLimit: integer('alerts_limit').default(3),
  billingCycleStart: timestamp('billing_cycle_start').defaultNow(),
  phonepeCustomerId: text('phonepe_customer_id'),
  lastPaymentAt: timestamp('last_payment_at'),
});

export const activityLogs = pgTable('activity_logs', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').references(() => users.id),
  action: text('action').notNull(),
  timestamp: timestamp('timestamp').notNull().defaultNow(),
  ipAddress: varchar('ip_address', { length: 45 }),
});

export const incidents = pgTable('incidents', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
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
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  metricType: varchar('metric_type', { length: 50 }).notNull(), // response_time, health_score, incident_count, etc.
  value: text('value').notNull(), // storing as text to handle different value types
  timestamp: timestamp('timestamp').notNull().defaultNow(),
  metadata: text('metadata'), // JSON string for additional data
});

export const aiActions = pgTable('ai_actions', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  incidentId: integer('incident_id').references(() => incidents.id),
  action: varchar('action', { length: 100 }).notNull(),
  description: text('description'),
  status: varchar('status', { length: 20 }).notNull().default('completed'), // pending, completed, failed
  aiAgent: varchar('ai_agent', { length: 50 }).notNull().default('oncall-agent'),
  approvedBy: integer('approved_by').references(() => users.id),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  metadata: text('metadata'), // JSON string for additional data
});

export const alertUsage = pgTable('alert_usage', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  incidentId: integer('incident_id').references(() => incidents.id),
  alertType: varchar('alert_type', { length: 50 }).notNull(),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  metadata: text('metadata'),
});

export const paymentTransactions = pgTable('payment_transactions', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  transactionId: varchar('transaction_id', { length: 255 }).notNull().unique(),
  amount: integer('amount').notNull(),
  currency: varchar('currency', { length: 10 }).default('INR'),
  planName: varchar('plan_name', { length: 50 }).notNull(),
  status: varchar('status', { length: 20 }).notNull(),
  paymentMethod: varchar('payment_method', { length: 50 }),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  completedAt: timestamp('completed_at'),
  metadata: text('metadata'),
});

export const subscriptionPlans = pgTable('subscription_plans', {
  id: serial('id').primaryKey(),
  planId: varchar('plan_id', { length: 50 }).notNull().unique(),
  name: varchar('name', { length: 100 }).notNull(),
  displayName: varchar('display_name', { length: 100 }).notNull(),
  price: integer('price').notNull(),
  currency: varchar('currency', { length: 10 }).default('INR'),
  alertsLimit: integer('alerts_limit').notNull(),
  features: text('features').notNull(), // JSON array
  isActive: integer('is_active').default(1),
  createdAt: timestamp('created_at').notNull().defaultNow(),
});

export const integrations = pgTable('integrations', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
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

export const userApiKeys = pgTable('user_api_keys', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  provider: varchar('provider', { length: 20 }).notNull(),
  name: varchar('name', { length: 100 }).notNull(),
  keyMasked: varchar('key_masked', { length: 20 }).notNull(),
  keyHash: text('key_hash').notNull(),
  isPrimary: boolean('is_primary').notNull().default(false),
  status: varchar('status', { length: 20 }).notNull().default('active'),
  model: varchar('model', { length: 50 }),
  isValidated: boolean('is_validated').notNull().default(false),
  validatedAt: timestamp('validated_at'),
  validationError: text('validation_error'),
  rateLimitRemaining: integer('rate_limit_remaining'),
  rateLimitResetAt: timestamp('rate_limit_reset_at'),
  errorCount: integer('error_count').notNull().default(0),
  lastError: text('last_error'),
  lastUsedAt: timestamp('last_used_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
});

export const userSetupRequirements = pgTable('user_setup_requirements', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  requirementType: varchar('requirement_type', { length: 50 }).notNull(),
  isCompleted: boolean('is_completed').notNull().default(false),
  isRequired: boolean('is_required').notNull().default(true),
  completedAt: timestamp('completed_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
});

export const setupValidationLogs = pgTable('setup_validation_logs', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .notNull()
    .references(() => users.id),
  validationType: varchar('validation_type', { length: 50 }).notNull(),
  validationTarget: varchar('validation_target', { length: 100 }).notNull(),
  isSuccessful: boolean('is_successful').notNull(),
  errorMessage: text('error_message'),
  metadata: jsonb('metadata'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
});

// Relations
export const usersRelations = relations(users, ({ many }) => ({
  activityLogs: many(activityLogs),
  incidents: many(incidents),
  assignedIncidents: many(incidents, { relationName: 'assignedIncidents' }),
  resolvedIncidents: many(incidents, { relationName: 'resolvedIncidents' }),
  incidentLogs: many(incidentLogs),
  metrics: many(metrics),
  aiActions: many(aiActions),
  approvedAiActions: many(aiActions, { relationName: 'approvedAiActions' }),
  alertUsage: many(alertUsage),
  paymentTransactions: many(paymentTransactions),
  integrations: many(integrations),
  createdIntegrations: many(integrations, { relationName: 'createdIntegrations' }),
  updatedIntegrations: many(integrations, { relationName: 'updatedIntegrations' }),
  apiKeys: many(userApiKeys),
  setupRequirements: many(userSetupRequirements),
  setupValidationLogs: many(setupValidationLogs),
}));

export const activityLogsRelations = relations(activityLogs, ({ one }) => ({
  user: one(users, {
    fields: [activityLogs.userId],
    references: [users.id],
  }),
}));

export const incidentsRelations = relations(incidents, ({ one, many }) => ({
  user: one(users, {
    fields: [incidents.userId],
    references: [users.id],
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
  alertUsage: many(alertUsage),
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
  user: one(users, {
    fields: [metrics.userId],
    references: [users.id],
  }),
}));

export const aiActionsRelations = relations(aiActions, ({ one }) => ({
  user: one(users, {
    fields: [aiActions.userId],
    references: [users.id],
  }),
  incident: one(incidents, {
    fields: [aiActions.incidentId],
    references: [incidents.id],
  }),
  approvedBy: one(users, {
    fields: [aiActions.approvedBy],
    references: [users.id],
    relationName: 'approvedAiActions',
  }),
}));

export const alertUsageRelations = relations(alertUsage, ({ one }) => ({
  user: one(users, {
    fields: [alertUsage.userId],
    references: [users.id],
  }),
  incident: one(incidents, {
    fields: [alertUsage.incidentId],
    references: [incidents.id],
  }),
}));

export const paymentTransactionsRelations = relations(paymentTransactions, ({ one }) => ({
  user: one(users, {
    fields: [paymentTransactions.userId],
    references: [users.id],
  }),
}));

export const integrationsRelations = relations(integrations, ({ one }) => ({
  user: one(users, {
    fields: [integrations.userId],
    references: [users.id],
  }),
  createdBy: one(users, {
    fields: [integrations.createdBy],
    references: [users.id],
    relationName: 'createdIntegrations',
  }),
  updatedBy: one(users, {
    fields: [integrations.updatedBy],
    references: [users.id],
    relationName: 'updatedIntegrations',
  }),
}));

export const userApiKeysRelations = relations(userApiKeys, ({ one }) => ({
  user: one(users, {
    fields: [userApiKeys.userId],
    references: [users.id],
  }),
}));

export const userSetupRequirementsRelations = relations(userSetupRequirements, ({ one }) => ({
  user: one(users, {
    fields: [userSetupRequirements.userId],
    references: [users.id],
  }),
}));

export const setupValidationLogsRelations = relations(setupValidationLogs, ({ one }) => ({
  user: one(users, {
    fields: [setupValidationLogs.userId],
    references: [users.id],
  }),
}));

// Type exports
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type ActivityLog = typeof activityLogs.$inferSelect;
export type NewActivityLog = typeof activityLogs.$inferInsert;
export type Incident = typeof incidents.$inferSelect;
export type NewIncident = typeof incidents.$inferInsert;
export type IncidentLog = typeof incidentLogs.$inferSelect;
export type NewIncidentLog = typeof incidentLogs.$inferInsert;
export type Metric = typeof metrics.$inferSelect;
export type NewMetric = typeof metrics.$inferInsert;
export type AiAction = typeof aiActions.$inferSelect;
export type NewAiAction = typeof aiActions.$inferInsert;
export type AlertUsage = typeof alertUsage.$inferSelect;
export type NewAlertUsage = typeof alertUsage.$inferInsert;
export type PaymentTransaction = typeof paymentTransactions.$inferSelect;
export type NewPaymentTransaction = typeof paymentTransactions.$inferInsert;
export type SubscriptionPlan = typeof subscriptionPlans.$inferSelect;
export type NewSubscriptionPlan = typeof subscriptionPlans.$inferInsert;
export type Integration = typeof integrations.$inferSelect;
export type NewIntegration = typeof integrations.$inferInsert;
export type UserApiKey = typeof userApiKeys.$inferSelect;
export type NewUserApiKey = typeof userApiKeys.$inferInsert;
export type UserSetupRequirement = typeof userSetupRequirements.$inferSelect;
export type NewUserSetupRequirement = typeof userSetupRequirements.$inferInsert;
export type SetupValidationLog = typeof setupValidationLogs.$inferSelect;
export type NewSetupValidationLog = typeof setupValidationLogs.$inferInsert;

export enum ActivityType {
  SIGN_UP = 'SIGN_UP',
  SIGN_IN = 'SIGN_IN',
  SIGN_OUT = 'SIGN_OUT',
  UPDATE_PASSWORD = 'UPDATE_PASSWORD',
  DELETE_ACCOUNT = 'DELETE_ACCOUNT',
  UPDATE_ACCOUNT = 'UPDATE_ACCOUNT',
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

export enum SetupRequirementType {
  LLM_CONFIG = 'llm_config',
  PAGERDUTY = 'pagerduty',
  KUBERNETES = 'kubernetes',
  GITHUB = 'github',
  NOTION = 'notion',
  GRAFANA = 'grafana',
  DATADOG = 'datadog',
}

export enum LLMProvider {
  ANTHROPIC = 'anthropic',
  OPENAI = 'openai',
}