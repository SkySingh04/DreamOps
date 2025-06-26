# Database Setup Guide

This guide covers setting up three separate Neon databases for local development, staging, and production environments with complete data isolation.

## Overview

The platform uses separate databases for different environments to ensure complete data isolation:
- **Local**: For development with local database
- **Staging**: For testing with staging database  
- **Production**: For production with production database

## Step 1: Create Neon Projects

1. Go to [neon.tech](https://neon.tech) and create 3 separate projects:
   - `dreamops-local` - For local development
   - `dreamops-staging` - For staging/testing
   - `dreamops-prod` - For production

2. For each project:
   - Region: Choose closest to you (e.g., US East, EU Central)
   - Database name: `oncall_agent`
   - Branch: Keep main branch

## Step 2: Configure Environment Files

### Backend Configuration

Create these files in your `backend/` directory:

```bash
# .env.local (for local development)
DATABASE_URL=postgresql://[your-local-neon-connection-string]
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=DEBUG
ENVIRONMENT=local

# .env.staging
DATABASE_URL=postgresql://[your-staging-neon-connection-string]
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=INFO
ENVIRONMENT=staging

# .env.production
DATABASE_URL=postgresql://[your-prod-neon-connection-string]
ANTHROPIC_API_KEY=your-anthropic-key
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Frontend Configuration

Create these files in your `frontend/` directory:

```bash
# .env.local
POSTGRES_URL=postgresql://[your-local-neon-connection-string]
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=local

# .env.staging
POSTGRES_URL=postgresql://[your-staging-neon-connection-string]
NEXT_PUBLIC_API_URL=https://api-staging.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=staging

# .env.production
POSTGRES_URL=postgresql://[your-prod-neon-connection-string]
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=production
```

## Step 3: Database Migrations

Run migrations for each environment:

```bash
cd frontend

# Local
npm run db:migrate:local      # Auto-migrates

# Staging
npm run db:migrate:staging    # Auto-migrates

# Production (be careful!)
npm run db:migrate:production # Requires confirmation
```

## Step 4: Database Testing

### Automated Testing
```bash
cd frontend
npm run test:db  # Tests all database connections
```

### Manual Testing with psql
```bash
# Test each connection
psql "your-local-connection-string" -c "SELECT current_database(), 'LOCAL' as env;"
psql "your-staging-connection-string" -c "SELECT current_database(), 'STAGING' as env;"
psql "your-prod-connection-string" -c "SELECT current_database(), 'PRODUCTION' as env;"
```

### Using Drizzle Studio
```bash
cd frontend

# View LOCAL database
npm run db:studio              # Opens at http://localhost:4983

# View STAGING database
POSTGRES_URL="your-staging-connection-string" npm run db:studio

# View PRODUCTION database (be careful!)
POSTGRES_URL="your-prod-connection-string" npm run db:studio
```

## Database Verification

To verify your databases are properly separated:

1. **Create test data in each environment** to ensure isolation
2. **Check that data doesn't leak between environments**
3. **Verify each database has unique connection strings**

## Quick Database Testing

For rapid database testing:

```bash
# Step 1: Set up Neon projects (dreamops-local, dreamops-staging, dreamops-prod)
# Step 2: Create environment files with connection strings
# Step 3: Run tests

cd frontend
npm install postgres
node test-db-connections.mjs
```

Expected output:
```
🚀 DreamOps Database Connection Tests
=====================================

🔍 Testing LOCAL database...
   ✅ Connected successfully!
   📊 Database: oncall_agent
   👤 User: your_user

🔍 Testing STAGING database...
   ✅ Connected successfully!

🔍 Testing PRODUCTION database...
   ✅ Connected successfully!

🔒 Database Separation Check
============================
✅ Perfect! All 3 environments use different databases.
```

## Database Schema Management

### Schema Design
The database schema is defined in `frontend/lib/db/schema.ts` using Drizzle ORM:
- **Users**: Authentication and authorization
- **Teams**: Multi-tenancy support
- **Incidents**: Incident tracking and history
- **Metrics**: Performance and analytics data
- **Logs**: Agent execution logs

### Migration Strategy
1. **Local Development**: Auto-migrate with `npm run db:migrate:local`
2. **Staging**: Manual migration with `npm run db:migrate:staging`
3. **Production**: Confirmation required with `npm run db:migrate:production`

### Database Testing Utilities
```bash
cd frontend
node test-db-connections.mjs  # Test all connections
npm run db:studio            # Visual database exploration
```

## Troubleshooting

### Connection Issues
**Problem**: Connection timeouts or SSL errors

**Solution**: 
1. Verify connection strings include `?sslmode=require`
2. Check Neon project is active (not suspended)
3. Ensure no `&channel_binding=require` in connection string

### Migration Issues
**Problem**: Migration failures

**Solution**:
1. Check database permissions
2. Verify connection string format
3. Ensure database is accessible
4. Check for conflicting schema changes

## Security Notes

- Never commit .env files to git
- Use environment variables in CI/CD pipelines
- Keep production credentials completely separate
- Each environment has its own isolated database
- Rotate database credentials regularly
- Use least-privilege database users 