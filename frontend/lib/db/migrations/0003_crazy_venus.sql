CREATE TABLE "integration_audit_logs" (
	"id" serial PRIMARY KEY NOT NULL,
	"team_id" integer NOT NULL,
	"integration_id" uuid NOT NULL,
	"action" varchar(50) NOT NULL,
	"performed_by" integer NOT NULL,
	"previous_config" jsonb,
	"new_config" jsonb,
	"result" varchar(20),
	"error_message" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"metadata" jsonb
);
--> statement-breakpoint
CREATE TABLE "setup_validation_logs" (
	"id" serial PRIMARY KEY NOT NULL,
	"user_id" integer NOT NULL,
	"validation_type" varchar(50) NOT NULL,
	"validation_target" varchar(100) NOT NULL,
	"is_successful" boolean NOT NULL,
	"error_message" text,
	"metadata" jsonb,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "team_integrations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"team_id" integer NOT NULL,
	"integration_type" varchar(50) NOT NULL,
	"config" jsonb NOT NULL,
	"is_enabled" boolean DEFAULT true NOT NULL,
	"is_required" boolean DEFAULT false NOT NULL,
	"last_test_at" timestamp,
	"last_test_status" varchar(20),
	"last_test_error" text,
	"created_by" integer NOT NULL,
	"updated_by" integer NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "user_setup_requirements" (
	"id" serial PRIMARY KEY NOT NULL,
	"user_id" integer NOT NULL,
	"requirement_type" varchar(50) NOT NULL,
	"is_completed" boolean DEFAULT false NOT NULL,
	"is_required" boolean DEFAULT true NOT NULL,
	"completed_at" timestamp,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "api_keys" ADD COLUMN "model" varchar(50);--> statement-breakpoint
ALTER TABLE "api_keys" ADD COLUMN "is_validated" boolean DEFAULT false NOT NULL;--> statement-breakpoint
ALTER TABLE "api_keys" ADD COLUMN "validated_at" timestamp;--> statement-breakpoint
ALTER TABLE "api_keys" ADD COLUMN "validation_error" text;--> statement-breakpoint
ALTER TABLE "api_keys" ADD COLUMN "rate_limit_remaining" integer;--> statement-breakpoint
ALTER TABLE "api_keys" ADD COLUMN "rate_limit_reset_at" timestamp;--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "llm_provider" varchar(20);--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "llm_model" varchar(50);--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "is_setup_complete" boolean DEFAULT false NOT NULL;--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "setup_completed_at" timestamp;--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "last_validation_at" timestamp;--> statement-breakpoint
ALTER TABLE "integration_audit_logs" ADD CONSTRAINT "integration_audit_logs_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "integration_audit_logs" ADD CONSTRAINT "integration_audit_logs_integration_id_team_integrations_id_fk" FOREIGN KEY ("integration_id") REFERENCES "public"."team_integrations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "integration_audit_logs" ADD CONSTRAINT "integration_audit_logs_performed_by_users_id_fk" FOREIGN KEY ("performed_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "setup_validation_logs" ADD CONSTRAINT "setup_validation_logs_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "team_integrations" ADD CONSTRAINT "team_integrations_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "team_integrations" ADD CONSTRAINT "team_integrations_created_by_users_id_fk" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "team_integrations" ADD CONSTRAINT "team_integrations_updated_by_users_id_fk" FOREIGN KEY ("updated_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "user_setup_requirements" ADD CONSTRAINT "user_setup_requirements_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;