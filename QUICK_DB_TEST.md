# Quick Database Testing Guide

## Step 1: Set Up Your Neon Projects

1. **Go to [neon.tech](https://neon.tech)** and create 3 projects:
   - `dreamops-local`
   - `dreamops-staging`  
   - `dreamops-prod`

2. **Get connection strings** from each project's dashboard

## Step 2: Create Your Environment Files

### Backend Setup:
```bash
cd backend

# Create LOCAL env file
cp .env.local.example .env.local
# Edit .env.local and paste your LOCAL Neon connection string

# Create STAGING env file  
cp .env.staging.example .env.staging
# Edit .env.staging and paste your STAGING Neon connection string

# Create PRODUCTION env file
cp .env.production.example .env.production  
# Edit .env.production and paste your PRODUCTION Neon connection string
```

### Frontend Setup:
```bash
cd ../frontend

# Create LOCAL env file (if not exists)
cat > .env.local << 'EOF'
POSTGRES_URL=your-local-neon-connection-string-here
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=local
BASE_URL=http://localhost:3000
AUTH_SECRET=dev-secret-change-in-production
EOF

# Create STAGING env file
cat > .env.staging << 'EOF'
POSTGRES_URL=your-staging-neon-connection-string-here
NEXT_PUBLIC_API_URL=https://api-staging.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=staging
BASE_URL=https://staging.yourdomain.com
AUTH_SECRET=${AUTH_SECRET_STAGING}
EOF

# Create PRODUCTION env file
cat > .env.production << 'EOF'
POSTGRES_URL=your-prod-neon-connection-string-here
NEXT_PUBLIC_API_URL=https://api.yourdomain.com  
NEXT_PUBLIC_ENVIRONMENT=production
BASE_URL=https://app.yourdomain.com
AUTH_SECRET=${AUTH_SECRET_PROD}
EOF
```

## Step 3: Run the Tests

### Backend Test (Python):
```bash
cd backend

# Install required package
pip install asyncpg python-dotenv

# Run the test
python test_db_connections.py

# Optional: Clean up old test tables
python test_db_connections.py --cleanup
```

### Frontend Test (Node.js):
```bash
cd frontend

# Make sure postgres package is installed
npm install postgres

# Run the test
node test-db-connections.mjs
```

## Step 4: What You Should See

### Successful Test Output:
```
🚀 DreamOps Database Connection Tests
=====================================

🔍 Testing LOCAL database...
   Connection: postgresql://user:***@ep-local-123.region.aws.neon.tech/oncall_agent
   ✅ Connected successfully!
   📊 Database: oncall_agent
   👤 User: your_user
   📋 Tables found: 0
   ✅ Created test table: test_local_1703123456
   ✅ Inserted test data with ID: LOCAL-1703123456-test
   ✅ Verified data: env=LOCAL, id=LOCAL-1703123456-test
   🧹 Cleaned up test table

🔍 Testing STAGING database...
   [Similar output but different database]

🔍 Testing PRODUCTION database...
   [Similar output but different database]

📊 Test Summary
===============
✅ LOCAL: Connected to oncall_agent
✅ STAGING: Connected to oncall_agent  
✅ PRODUCTION: Connected to oncall_agent

🔒 Database Separation Check
============================
✅ Perfect! All 3 environments use different databases.
   Your data is properly isolated between environments.
```

## Step 5: Manual Verification

### Using Neon Dashboard:
1. Open 3 browser tabs
2. Go to each Neon project
3. Click on "Tables" in each project
4. You should see NO shared data between them

### Using psql Command Line:
```bash
# Test each connection
psql "your-local-connection-string" -c "SELECT current_database(), 'LOCAL' as env;"
psql "your-staging-connection-string" -c "SELECT current_database(), 'STAGING' as env;"
psql "your-prod-connection-string" -c "SELECT current_database(), 'PRODUCTION' as env;"
```

### Using Drizzle Studio:
```bash
cd frontend

# View LOCAL database
POSTGRES_URL="your-local-connection-string" npm run db:studio

# View STAGING database (in new terminal)
POSTGRES_URL="your-staging-connection-string" npm run db:studio

# View PRODUCTION database (be careful!)
POSTGRES_URL="your-prod-connection-string" npm run db:studio
```

## Step 6: Create Test Data to Verify Isolation

### In LOCAL Database:
```sql
-- Connect to LOCAL database
CREATE TABLE local_only (
    id SERIAL PRIMARY KEY,
    message TEXT DEFAULT 'This should only exist in LOCAL',
    created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO local_only (message) VALUES ('LOCAL TEST DATA');
```

### In STAGING Database:
```sql
-- Connect to STAGING database  
CREATE TABLE staging_only (
    id SERIAL PRIMARY KEY,
    message TEXT DEFAULT 'This should only exist in STAGING',
    created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO staging_only (message) VALUES ('STAGING TEST DATA');
```

### Verify Isolation:
- Check LOCAL database - should ONLY see `local_only` table
- Check STAGING database - should ONLY see `staging_only` table
- Check PRODUCTION database - should see neither table

## Common Issues and Fixes

### "No DATABASE_URL found"
- Make sure you created the .env files
- Check the file names match exactly (.env.local, not .env.local.txt)

### "Connection timeout"
- Verify your Neon project is active
- Check the connection string is complete (includes ?sslmode=require)

### "SSL required"
- Neon requires SSL - make sure your connection string ends with `?sslmode=require`

### "All using same database"
- You might have copied the same connection string to all files
- Each Neon project has a UNIQUE connection string

## Next Steps After Testing

1. **Run migrations on each database:**
   ```bash
   cd frontend
   
   # Migrate LOCAL
   npm run db:migrate
   
   # Migrate STAGING
   POSTGRES_URL="staging-connection" npm run db:migrate
   
   # Migrate PRODUCTION (be careful!)
   POSTGRES_URL="prod-connection" npm run db:migrate
   ```

2. **Set up GitHub Secrets:**
   - Go to your repo Settings → Secrets
   - Add `NEON_DATABASE_URL_STAGING`
   - Add `NEON_DATABASE_URL_PROD`

3. **Update your deployment scripts** to use the appropriate database

## 🎉 Success Checklist

- [ ] Created 3 separate Neon projects
- [ ] Each project has its own connection string
- [ ] Backend has 3 env files (.env.local, .env.staging, .env.production)
- [ ] Frontend has 3 env files (.env.local, .env.staging, .env.production)
- [ ] Connection test shows 3 different databases
- [ ] Test data in one database doesn't appear in others
- [ ] Added .env files to .gitignore