-- Remove team-related foreign keys and columns
ALTER TABLE users DROP COLUMN IF EXISTS team_id;
ALTER TABLE incidents DROP COLUMN IF EXISTS team_id;
ALTER TABLE metrics DROP COLUMN IF EXISTS team_id;
ALTER TABLE ai_actions DROP COLUMN IF EXISTS team_id;
ALTER TABLE activity_logs DROP COLUMN IF EXISTS team_id;

-- Drop team-related tables
DROP TABLE IF EXISTS integration_audit_logs;
DROP TABLE IF EXISTS team_integrations;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS invitations;
DROP TABLE IF EXISTS team_members;
DROP TABLE IF EXISTS teams;

-- Create new integrations table without team dependency
CREATE TABLE IF NOT EXISTS integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_type VARCHAR(50) NOT NULL,
  config JSONB NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT true,
  is_required BOOLEAN NOT NULL DEFAULT false,
  last_test_at TIMESTAMP,
  last_test_status VARCHAR(20),
  last_test_error TEXT,
  created_by INTEGER NOT NULL REFERENCES users(id),
  updated_by INTEGER NOT NULL REFERENCES users(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create new api_keys table without team dependency
CREATE TABLE IF NOT EXISTS user_api_keys (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  provider VARCHAR(20) NOT NULL,
  name VARCHAR(100) NOT NULL,
  key_masked VARCHAR(20) NOT NULL,
  key_hash TEXT NOT NULL,
  is_primary BOOLEAN NOT NULL DEFAULT false,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  model VARCHAR(50),
  is_validated BOOLEAN NOT NULL DEFAULT false,
  validated_at TIMESTAMP,
  validation_error TEXT,
  rate_limit_remaining INTEGER,
  rate_limit_reset_at TIMESTAMP,
  last_used_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);