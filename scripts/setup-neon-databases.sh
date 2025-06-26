#!/bin/bash

# DreamOps Neon Database Setup Script
# This script helps you set up your three Neon databases

echo "🚀 DreamOps Neon Database Setup"
echo "================================"
echo ""
echo "This script will help you configure your database environments."
echo "You'll need to have already created 3 Neon projects:"
echo "  1. oncall-local (for development)"
echo "  2. oncall-staging (for testing)"
echo "  3. oncall-prod (for production)"
echo ""
echo "Press Enter to continue..."
read

# Function to validate connection string
validate_connection() {
    if [[ $1 =~ ^postgresql://.*@.*\.neon\.tech/.*$ ]]; then
        return 0
    else
        return 1
    fi
}

# Collect connection strings
echo ""
echo "📝 Step 1: Enter your Neon connection strings"
echo "---------------------------------------------"

# Local
echo ""
echo "Enter your LOCAL Neon connection string:"
echo "(From oncall-local project in Neon dashboard)"
read -r LOCAL_DB_URL
while ! validate_connection "$LOCAL_DB_URL"; do
    echo "❌ Invalid connection string. It should look like:"
    echo "   postgresql://user:pass@ep-name-123.region.aws.neon.tech/oncall_agent?sslmode=require"
    echo "Please try again:"
    read -r LOCAL_DB_URL
done

# Staging
echo ""
echo "Enter your STAGING Neon connection string:"
echo "(From oncall-staging project in Neon dashboard)"
read -r STAGING_DB_URL
while ! validate_connection "$STAGING_DB_URL"; do
    echo "❌ Invalid connection string. Please try again:"
    read -r STAGING_DB_URL
done

# Production
echo ""
echo "Enter your PRODUCTION Neon connection string:"
echo "(From oncall-prod project in Neon dashboard)"
read -r PROD_DB_URL
while ! validate_connection "$PROD_DB_URL"; do
    echo "❌ Invalid connection string. Please try again:"
    read -r PROD_DB_URL
done

# Create backend env files
echo ""
echo "📁 Step 2: Creating backend environment files"
echo "--------------------------------------------"

# Backend .env.local
if [ -f "backend/.env.local.example" ]; then
    cp backend/.env.local.example backend/.env.local
    # Replace the placeholder with actual connection string
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$LOCAL_DB_URL|" backend/.env.local
    echo "✅ Created backend/.env.local"
fi

# Backend .env.staging
if [ -f "backend/.env.staging.example" ]; then
    cp backend/.env.staging.example backend/.env.staging
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$STAGING_DB_URL|" backend/.env.staging
    echo "✅ Created backend/.env.staging"
fi

# Backend .env.production
if [ -f "backend/.env.production.example" ]; then
    cp backend/.env.production.example backend/.env.production
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$PROD_DB_URL|" backend/.env.production
    echo "✅ Created backend/.env.production"
fi

# Create frontend env files
echo ""
echo "📁 Step 3: Creating frontend environment files"
echo "---------------------------------------------"

# Frontend .env.local
cat > frontend/.env.local << EOF
# Local Development Database
POSTGRES_URL=$LOCAL_DB_URL

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=local

# Copy other settings from .env.example
BASE_URL=http://localhost:3000
AUTH_SECRET=your-auth-secret-here

# Stripe (if needed)
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
EOF
echo "✅ Created frontend/.env.local"

# Frontend .env.staging
cat > frontend/.env.staging << EOF
# Staging Database
POSTGRES_URL=$STAGING_DB_URL

# API Configuration
NEXT_PUBLIC_API_URL=https://api-staging.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=staging

# Copy other settings from .env.example
BASE_URL=https://staging.yourdomain.com
AUTH_SECRET=\${AUTH_SECRET_STAGING}

# Stripe (if needed)
STRIPE_SECRET_KEY=\${STRIPE_SECRET_KEY_STAGING}
STRIPE_WEBHOOK_SECRET=\${STRIPE_WEBHOOK_SECRET_STAGING}
EOF
echo "✅ Created frontend/.env.staging"

# Frontend .env.production
cat > frontend/.env.production << EOF
# Production Database
POSTGRES_URL=$PROD_DB_URL

# API Configuration
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=production

# Copy other settings from .env.example
BASE_URL=https://app.yourdomain.com
AUTH_SECRET=\${AUTH_SECRET_PROD}

# Stripe (if needed)
STRIPE_SECRET_KEY=\${STRIPE_SECRET_KEY_PROD}
STRIPE_WEBHOOK_SECRET=\${STRIPE_WEBHOOK_SECRET_PROD}
EOF
echo "✅ Created frontend/.env.production"

# Clean up backup files
rm -f backend/.env.*.bak

# Create .gitignore entries
echo ""
echo "📝 Step 4: Updating .gitignore"
echo "------------------------------"

# Add to backend/.gitignore if not already there
if ! grep -q ".env.local" backend/.gitignore 2>/dev/null; then
    echo -e "\n# Environment files\n.env.local\n.env.staging\n.env.production" >> backend/.gitignore
    echo "✅ Updated backend/.gitignore"
fi

# Add to frontend/.gitignore if not already there
if ! grep -q ".env.staging" frontend/.gitignore 2>/dev/null; then
    echo -e "\n# Environment files\n.env.staging\n.env.production" >> frontend/.gitignore
    echo "✅ Updated frontend/.gitignore"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo ""
echo "1. Update your Anthropic API key in the backend .env files"
echo "2. For local development:"
echo "   cd backend && cp .env.local .env"
echo "   cd frontend && npm run db:migrate"
echo ""
echo "3. Test your connection:"
echo "   cd frontend && npm run db:studio"
echo ""
echo "4. Set up GitHub secrets for CI/CD:"
echo "   - NEON_DATABASE_URL_STAGING = $STAGING_DB_URL"
echo "   - NEON_DATABASE_URL_PROD = $PROD_DB_URL"
echo ""
echo "⚠️  Security reminder: Never commit these .env files to Git!"
echo ""