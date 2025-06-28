-- Add missing columns to users table
DO $$ 
BEGIN
    -- Add is_setup_complete column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'is_setup_complete') THEN
        ALTER TABLE users ADD COLUMN is_setup_complete BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;

    -- Add setup_completed_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'setup_completed_at') THEN
        ALTER TABLE users ADD COLUMN setup_completed_at TIMESTAMP;
    END IF;

    -- Add last_validation_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'last_validation_at') THEN
        ALTER TABLE users ADD COLUMN last_validation_at TIMESTAMP;
    END IF;

    -- Add llm_provider column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'llm_provider') THEN
        ALTER TABLE users ADD COLUMN llm_provider VARCHAR(20);
    END IF;

    -- Add llm_model column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'llm_model') THEN
        ALTER TABLE users ADD COLUMN llm_model VARCHAR(50);
    END IF;

    -- Add role column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'role') THEN
        ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'member';
    END IF;

    -- Add password_hash column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'password_hash') THEN
        ALTER TABLE users ADD COLUMN password_hash TEXT;
    END IF;

    -- Add deleted_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'deleted_at') THEN
        ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP;
    END IF;

    -- Add payment related columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'stripe_customer_id') THEN
        ALTER TABLE users ADD COLUMN stripe_customer_id TEXT UNIQUE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'stripe_subscription_id') THEN
        ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT UNIQUE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'stripe_product_id') THEN
        ALTER TABLE users ADD COLUMN stripe_product_id TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'plan_name') THEN
        ALTER TABLE users ADD COLUMN plan_name VARCHAR(50);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'subscription_status') THEN
        ALTER TABLE users ADD COLUMN subscription_status VARCHAR(20);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'account_tier') THEN
        ALTER TABLE users ADD COLUMN account_tier VARCHAR(20) DEFAULT 'free';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'alerts_used') THEN
        ALTER TABLE users ADD COLUMN alerts_used INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'alerts_limit') THEN
        ALTER TABLE users ADD COLUMN alerts_limit INTEGER DEFAULT 3;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'billing_cycle_start') THEN
        ALTER TABLE users ADD COLUMN billing_cycle_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'phonepe_customer_id') THEN
        ALTER TABLE users ADD COLUMN phonepe_customer_id TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'last_payment_at') THEN
        ALTER TABLE users ADD COLUMN last_payment_at TIMESTAMP;
    END IF;
END $$;

-- Create missing tables that are referenced in the schema
CREATE TABLE IF NOT EXISTS user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    provider VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    key_masked VARCHAR(20) NOT NULL,
    key_hash TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    model VARCHAR(50),
    is_validated BOOLEAN NOT NULL DEFAULT FALSE,
    validated_at TIMESTAMP,
    validation_error TEXT,
    rate_limit_remaining INTEGER,
    rate_limit_reset_at TIMESTAMP,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_setup_requirements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    requirement_type VARCHAR(50) NOT NULL,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS setup_validation_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    validation_type VARCHAR(50) NOT NULL,
    validation_target VARCHAR(100) NOT NULL,
    is_successful BOOLEAN NOT NULL,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id),
    integration_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    last_test_at TIMESTAMP,
    last_test_status VARCHAR(20),
    last_test_error TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id),
    updated_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kubernetes_credentials (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    cluster_name TEXT NOT NULL,
    auth_method TEXT NOT NULL CHECK (auth_method IN ('kubeconfig', 'service_account', 'client_cert', 'eks', 'gke', 'aks')),
    encrypted_credentials TEXT NOT NULL,
    namespace TEXT DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    connection_status TEXT DEFAULT 'pending' CHECK (connection_status IN ('pending', 'connected', 'failed', 'expired')),
    last_error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_setup_requirements_user_id ON user_setup_requirements(user_id);
CREATE INDEX IF NOT EXISTS idx_setup_validation_logs_user_id ON setup_validation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_integrations_user_id ON integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_k8s_credentials_user_id ON kubernetes_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_k8s_credentials_cluster_name ON kubernetes_credentials(cluster_name);
CREATE INDEX IF NOT EXISTS idx_k8s_credentials_is_active ON kubernetes_credentials(is_active);
CREATE UNIQUE INDEX IF NOT EXISTS idx_k8s_credentials_user_cluster ON kubernetes_credentials(user_id, cluster_name) WHERE is_active = true;