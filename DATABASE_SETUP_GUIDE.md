# Neon Database Setup Guide for DreamOps

## Overview
This guide will help you set up three separate Neon databases for local development, staging, and production environments.

## Step 1: Create Neon Accounts/Projects

### A. Sign up for Neon
1. Go to [neon.tech](https://neon.tech)
2. Sign up with GitHub/Google/Email
3. You'll get a free tier with 0.5 GB per project

### B. Create Three Projects
Create three separate projects in Neon:

1. **oncall-local** - For local development
2. **oncall-staging** - For staging/testing
3. **oncall-prod** - For production

For each project:
- Region: Choose closest to you (e.g., US East, EU Central)
- Database name: `oncall_agent`
- Branch: Keep main branch

## Step 2: Get Connection Strings

For each project, get the connection string:

1. Click on your project
2. Go to "Connection Details"
3. Copy the connection string (looks like):
   ```
   postgresql://username:password@ep-cool-darkness-123456.us-east-2.aws.neon.tech/oncall_agent?sslmode=require
   ```

## Step 3: Configure Your Environments

### A. Backend Configuration

Create these files in your `backend/` directory:

**`.env.local`** (for local development):
```env
# Database
DATABASE_URL=postgresql://[your-local-neon-connection-string]

# Core settings
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=DEBUG
ENVIRONMENT=local

# Other settings (copy from .env.example)
```

**`.env.staging`**:
```env
# Database
DATABASE_URL=postgresql://[your-staging-neon-connection-string]

# Core settings
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=INFO
ENVIRONMENT=staging

# Other settings
```

**`.env.production`**:
```env
# Database
DATABASE_URL=postgresql://[your-prod-neon-connection-string]

# Core settings
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=INFO
ENVIRONMENT=production

# Other settings
```

### B. Frontend Configuration

Create these files in your `frontend/` directory:

**`.env.local`**:
```env
# Database
POSTGRES_URL=postgresql://[your-local-neon-connection-string]

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=local

# Other settings from .env.example
```

**`.env.staging`**:
```env
# Database
POSTGRES_URL=postgresql://[your-staging-neon-connection-string]

# API
NEXT_PUBLIC_API_URL=https://api-staging.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=staging
```

**`.env.production`**:
```env
# Database
POSTGRES_URL=postgresql://[your-prod-neon-connection-string]

# API
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=production
```

## Step 4: Update Your Code

### A. Frontend Database Configuration

Update `frontend/lib/db/drizzle.ts`:

```typescript
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

// Get the appropriate database URL based on environment
const getDatabaseUrl = () => {
  const env = process.env.NODE_ENV || 'development';
  
  // For Vercel/production deployments
  if (process.env.POSTGRES_URL) {
    return process.env.POSTGRES_URL;
  }
  
  // For local development
  if (env === 'development') {
    return process.env.DATABASE_URL || process.env.POSTGRES_URL;
  }
  
  // Fallback
  throw new Error('Database URL not configured');
};

const connectionString = getDatabaseUrl();

// Create the connection
const client = postgres(connectionString, {
  ssl: 'require', // Neon requires SSL
  max: 1,
});

export const db = drizzle(client, { schema });
```

### B. Add Environment Indicator

Create `frontend/components/environment-indicator.tsx`:

```tsx
export function EnvironmentIndicator() {
  const env = process.env.NEXT_PUBLIC_ENVIRONMENT || 'local';
  
  if (env === 'production') return null;
  
  const colors = {
    local: 'bg-blue-500',
    staging: 'bg-yellow-500',
  };
  
  return (
    <div className={`fixed bottom-4 right-4 px-3 py-1 rounded text-white text-sm ${colors[env] || 'bg-gray-500'}`}>
      {env.toUpperCase()}
    </div>
  );
}
```

## Step 5: Database Migrations

### Running Migrations

For each environment:

```bash
# Local
cd frontend
npm run db:migrate

# Staging (manually specify the env file)
DATABASE_URL=$STAGING_DATABASE_URL npm run db:migrate

# Production (be careful!)
DATABASE_URL=$PRODUCTION_DATABASE_URL npm run db:migrate
```

### Creating Migration Scripts

Add to `frontend/package.json`:

```json
{
  "scripts": {
    "db:migrate:local": "drizzle-kit migrate",
    "db:migrate:staging": "dotenv -e .env.staging -- drizzle-kit migrate",
    "db:migrate:prod": "dotenv -e .env.production -- drizzle-kit migrate",
    "db:studio": "drizzle-kit studio"
  }
}
```

## Step 6: GitHub Actions Setup

### Store Secrets in GitHub

1. Go to your repo Settings → Secrets → Actions
2. Add these secrets:
   - `NEON_DATABASE_URL_STAGING` - Your staging Neon connection string
   - `NEON_DATABASE_URL_PROD` - Your production Neon connection string
   - `ANTHROPIC_API_KEY` - Your Anthropic API key

### Update Deployment Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main, staging]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set Environment Variables
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "ENVIRONMENT=production" >> $GITHUB_ENV
            echo "DATABASE_URL=${{ secrets.NEON_DATABASE_URL_PROD }}" >> $GITHUB_ENV
            echo "POSTGRES_URL=${{ secrets.NEON_DATABASE_URL_PROD }}" >> $GITHUB_ENV
          else
            echo "ENVIRONMENT=staging" >> $GITHUB_ENV
            echo "DATABASE_URL=${{ secrets.NEON_DATABASE_URL_STAGING }}" >> $GITHUB_ENV
            echo "POSTGRES_URL=${{ secrets.NEON_DATABASE_URL_STAGING }}" >> $GITHUB_ENV
          fi
      
      - name: Run Database Migrations
        run: |
          cd frontend
          npm install
          npm run db:migrate
      
      # Add your deployment steps here
```

## Step 7: Local Development Workflow

### Starting Local Development

```bash
# Terminal 1 - Backend
cd backend
cp .env.local .env  # Use local env
uv run python api_server.py

# Terminal 2 - Frontend
cd frontend
cp .env.local .env.local  # Next.js uses .env.local
npm run dev
```

### Switching Environments Locally

```bash
# To test with staging data locally
cd backend
cp .env.staging .env
uv run python api_server.py

cd frontend
cp .env.staging .env.local
npm run dev
```

## Step 8: Safety Best Practices

### 1. Database Branching (Neon Feature)

For safer production changes:

```bash
# In Neon dashboard, create a branch from production
# Test your migrations on the branch first
# Then apply to main branch
```

### 2. Backup Before Migrations

```sql
-- In Neon SQL editor
-- Create a backup table before major changes
CREATE TABLE users_backup AS SELECT * FROM users;
```

### 3. Read-Only Access

For production, consider creating a read-only user:

```sql
-- In Neon SQL editor for production
CREATE USER readonly_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE oncall_agent TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

## Step 9: Monitoring & Debugging

### Check Connection

```typescript
// Add to your API health check
async function checkDatabaseConnection() {
  try {
    const result = await db.execute('SELECT 1');
    return { connected: true, environment: process.env.ENVIRONMENT };
  } catch (error) {
    return { connected: false, error: error.message };
  }
}
```

### View Current Environment

Add to your frontend:

```tsx
// In your layout or dashboard
<div className="text-xs text-gray-500">
  Environment: {process.env.NEXT_PUBLIC_ENVIRONMENT || 'local'}
  {process.env.POSTGRES_URL?.includes('neon.tech') && ' (Neon)'}
</div>
```

## Cost Considerations

### Free Tier Limits (per project)
- 0.5 GB storage
- 10 GB bandwidth/month
- Always-on (no cold starts)

### For 3 Projects (Local + Staging + Prod)
- Total: 1.5 GB storage free
- 30 GB bandwidth/month free
- Cost: $0 for small team

### When You Might Need to Pay
- Storage > 0.5 GB per database
- High traffic (> 10 GB/month per database)
- Need more compute units
- Want point-in-time recovery

## Troubleshooting

### Common Issues

1. **SSL Connection Error**
   - Ensure `sslmode=require` in connection string
   - Or add `ssl: 'require'` in postgres client config

2. **Connection Timeout**
   - Check if IP is allowed (Neon allows all by default)
   - Verify connection string is correct
   - Check Neon dashboard for service status

3. **Migration Failures**
   - Ensure DATABASE_URL is set correctly
   - Check if tables already exist
   - Verify you have write permissions

### Useful Commands

```bash
# Test connection
psql "postgresql://[your-connection-string]" -c "SELECT version();"

# List all tables
psql "postgresql://[your-connection-string]" -c "\dt"

# Check database size
psql "postgresql://[your-connection-string]" -c "SELECT pg_database_size('oncall_agent');"
```

## Next Steps

1. Set up your three Neon projects
2. Configure your environment files
3. Run initial migrations
4. Test each environment
5. Set up CI/CD secrets
6. Document connection strings securely

Remember: Keep your production database connection string secure and never commit it to Git!