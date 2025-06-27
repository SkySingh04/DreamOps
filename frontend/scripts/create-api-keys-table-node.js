#!/usr/bin/env node
/**
 * Create API keys table using Node.js postgres driver
 */

const postgres = require('postgres');
const { readFileSync } = require('fs');
const path = require('path');

async function createTable() {
  try {
    // Load .env.local
    const envPath = path.join(__dirname, '..', '.env.local');
    const envContent = readFileSync(envPath, 'utf8');
    const postgresUrl = envContent.match(/POSTGRES_URL=(.+)/)?.[1];

    if (!postgresUrl) {
      console.error('POSTGRES_URL not found in .env.local');
      process.exit(1);
    }

    console.log('Creating API keys table...');

    const sql = postgres(postgresUrl);

    // Create the table
    await sql`
      CREATE TABLE IF NOT EXISTS "api_keys" (
        "id" serial PRIMARY KEY NOT NULL,
        "team_id" integer NOT NULL,
        "user_id" integer NOT NULL,
        "provider" varchar(20) NOT NULL,
        "name" varchar(100) NOT NULL,
        "key_masked" varchar(20) NOT NULL,
        "key_hash" text NOT NULL,
        "is_primary" boolean DEFAULT false NOT NULL,
        "status" varchar(20) DEFAULT 'active' NOT NULL,
        "error_count" integer DEFAULT 0 NOT NULL,
        "last_error" text,
        "last_used_at" timestamp,
        "created_at" timestamp DEFAULT now() NOT NULL,
        "updated_at" timestamp DEFAULT now() NOT NULL
      )
    `;

    // Add foreign key constraints
    try {
      await sql`
        ALTER TABLE "api_keys" 
        ADD CONSTRAINT "api_keys_team_id_teams_id_fk" 
        FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") 
        ON DELETE no action ON UPDATE no action
      `;
    } catch (e) {
      // Constraint might already exist
      console.log('Team FK constraint already exists or failed to add:', e.message);
    }

    try {
      await sql`
        ALTER TABLE "api_keys" 
        ADD CONSTRAINT "api_keys_user_id_users_id_fk" 
        FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") 
        ON DELETE no action ON UPDATE no action
      `;
    } catch (e) {
      // Constraint might already exist
      console.log('User FK constraint already exists or failed to add:', e.message);
    }

    await sql.end();
    console.log('✅ API keys table created successfully!');
  } catch (error) {
    console.error('❌ Failed to create table:', error.message);
    process.exit(1);
  }
}

createTable();