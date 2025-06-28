CREATE TABLE "alert_usage" (
	"id" serial PRIMARY KEY NOT NULL,
	"team_id" integer NOT NULL,
	"incident_id" integer,
	"alert_type" varchar(50) NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"metadata" text
);
--> statement-breakpoint
CREATE TABLE "payment_transactions" (
	"id" serial PRIMARY KEY NOT NULL,
	"team_id" integer NOT NULL,
	"transaction_id" varchar(255) NOT NULL,
	"amount" integer NOT NULL,
	"currency" varchar(10) DEFAULT 'INR',
	"plan_name" varchar(50) NOT NULL,
	"status" varchar(20) NOT NULL,
	"payment_method" varchar(50),
	"created_at" timestamp DEFAULT now() NOT NULL,
	"completed_at" timestamp,
	"metadata" text,
	CONSTRAINT "payment_transactions_transaction_id_unique" UNIQUE("transaction_id")
);
--> statement-breakpoint
CREATE TABLE "subscription_plans" (
	"id" serial PRIMARY KEY NOT NULL,
	"plan_id" varchar(50) NOT NULL,
	"name" varchar(100) NOT NULL,
	"display_name" varchar(100) NOT NULL,
	"price" integer NOT NULL,
	"currency" varchar(10) DEFAULT 'INR',
	"alerts_limit" integer NOT NULL,
	"features" text NOT NULL,
	"is_active" integer DEFAULT 1,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "subscription_plans_plan_id_unique" UNIQUE("plan_id")
);
--> statement-breakpoint
ALTER TABLE "teams" ADD COLUMN "account_tier" varchar(20) DEFAULT 'free';--> statement-breakpoint
ALTER TABLE "teams" ADD COLUMN "alerts_used" integer DEFAULT 0;--> statement-breakpoint
ALTER TABLE "teams" ADD COLUMN "alerts_limit" integer DEFAULT 3;--> statement-breakpoint
ALTER TABLE "teams" ADD COLUMN "billing_cycle_start" timestamp DEFAULT now();--> statement-breakpoint
ALTER TABLE "teams" ADD COLUMN "phonepe_customer_id" text;--> statement-breakpoint
ALTER TABLE "teams" ADD COLUMN "last_payment_at" timestamp;--> statement-breakpoint
ALTER TABLE "alert_usage" ADD CONSTRAINT "alert_usage_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "alert_usage" ADD CONSTRAINT "alert_usage_incident_id_incidents_id_fk" FOREIGN KEY ("incident_id") REFERENCES "public"."incidents"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "payment_transactions" ADD CONSTRAINT "payment_transactions_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;