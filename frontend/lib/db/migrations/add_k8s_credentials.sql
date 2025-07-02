-- Create table for storing encrypted Kubernetes credentials
CREATE TABLE IF NOT EXISTS kubernetes_credentials (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    cluster_name TEXT NOT NULL,
    auth_method TEXT NOT NULL CHECK (auth_method IN ('kubeconfig', 'service_account', 'client_cert', 'eks', 'gke', 'aks')),
    encrypted_credentials TEXT NOT NULL,
    namespace TEXT DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    connection_status TEXT DEFAULT 'pending' CHECK (connection_status IN ('pending', 'connected', 'failed', 'expired')),
    last_error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Add indexes
CREATE INDEX idx_k8s_credentials_user_id ON kubernetes_credentials(user_id);
CREATE INDEX idx_k8s_credentials_cluster_name ON kubernetes_credentials(cluster_name);
CREATE INDEX idx_k8s_credentials_is_active ON kubernetes_credentials(is_active);

-- Create unique constraint for user + cluster_name
CREATE UNIQUE INDEX idx_k8s_credentials_user_cluster ON kubernetes_credentials(user_id, cluster_name) WHERE is_active = true;