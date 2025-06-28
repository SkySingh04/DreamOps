-- Add firebase_uid column to users table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'firebase_uid') THEN
        ALTER TABLE users ADD COLUMN firebase_uid VARCHAR(128) UNIQUE;
    END IF;
END $$;

-- Create teams table (for backward compatibility)
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create invitations table
CREATE TABLE IF NOT EXISTS invitations (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    invited_by INTEGER REFERENCES users(id),
    token VARCHAR(255) UNIQUE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Create team_integrations table
CREATE TABLE IF NOT EXISTS team_integrations (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    integration_type VARCHAR(50) NOT NULL,
    config JSONB,
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create integration_audit_logs table
CREATE TABLE IF NOT EXISTS integration_audit_logs (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    user_id INTEGER REFERENCES users(id),
    integration_type VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create api_keys table (for backward compatibility with delete script)
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    key_hash TEXT NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

-- Add indexes only if columns exist
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'users' AND column_name = 'firebase_uid') THEN
        CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'invitations' AND column_name = 'email') THEN
        CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'invitations' AND column_name = 'token') THEN
        CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'api_keys' AND column_name = 'user_id') THEN
        CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
    END IF;
END $$;