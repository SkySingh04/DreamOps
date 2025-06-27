#!/bin/bash

# DreamOps Deployment Readiness Check Script
# This script verifies that everything is ready for Render deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 DreamOps Deployment Readiness Check${NC}"
echo "========================================"

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check if directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check if pattern exists in file
check_pattern() {
    if grep -q "$1" "$2" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $3"
        return 0
    else
        echo -e "${RED}✗${NC} $3"
        return 1
    fi
}

# Initialize counters
TOTAL_CHECKS=0
PASSED_CHECKS=0

# Backend Checks
echo -e "\n${YELLOW}Backend Checks:${NC}"
echo "---------------"

# Check backend directory
check_dir "backend" "Backend directory exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check requirements.txt
check_file "backend/requirements.txt" "requirements.txt exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check api_server.py
check_file "backend/api_server.py" "api_server.py exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check for PORT usage in api_server.py
check_pattern 'os.environ.get("PORT"' "backend/api_server.py" "api_server.py uses PORT env variable" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check for 0.0.0.0 binding
check_pattern 'host="0.0.0.0"' "backend/api_server.py" "api_server.py binds to 0.0.0.0" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check CORS configuration
check_pattern "cors_origins" "backend/src/oncall_agent/config.py" "CORS origins configurable" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check .env.example
check_file "backend/.env.example" "Backend .env.example exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Frontend Checks
echo -e "\n${YELLOW}Frontend Checks:${NC}"
echo "----------------"

# Check frontend directory
check_dir "frontend" "Frontend directory exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check package.json
check_file "frontend/package.json" "package.json exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check build script
check_pattern '"build":' "frontend/package.json" "Build script exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check start script with PORT
check_pattern '"start": "next start -p \$PORT"' "frontend/package.json" "Start script uses PORT variable" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check for NEXT_PUBLIC_API_URL usage
check_pattern "NEXT_PUBLIC_API_URL" "frontend/lib/api-client.ts" "API client uses NEXT_PUBLIC_API_URL" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Check .env.example
check_file "frontend/.env.example" "Frontend .env.example exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Deployment Files
echo -e "\n${YELLOW}Deployment Files:${NC}"
echo "-----------------"

# Check Render configuration files
check_file "render-staging.yaml" "render-staging.yaml exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

check_file "render-prod.yaml" "render-prod.yaml exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

check_file "DEPLOYMENT.md" "DEPLOYMENT.md documentation exists" && ((PASSED_CHECKS++))
((TOTAL_CHECKS++))

# Git Checks
echo -e "\n${YELLOW}Git Checks:${NC}"
echo "-----------"

# Check if we're in a git repository
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Git repository initialized"
    ((PASSED_CHECKS++))
    
    # Check for staging branch
    if git show-ref --verify --quiet refs/heads/staging; then
        echo -e "${GREEN}✓${NC} Staging branch exists"
        ((PASSED_CHECKS++))
    else
        echo -e "${YELLOW}!${NC} Staging branch not found (will be created during deployment)"
        ((PASSED_CHECKS++))
    fi
    
    # Check for uncommitted changes
    if [ -z "$(git status --porcelain)" ]; then
        echo -e "${GREEN}✓${NC} No uncommitted changes"
        ((PASSED_CHECKS++))
    else
        echo -e "${YELLOW}!${NC} Uncommitted changes detected"
        echo "   Run: git add . && git commit -m 'Prepare for deployment'"
    fi
else
    echo -e "${RED}✗${NC} Not a git repository"
fi
((TOTAL_CHECKS+=3))

# Environment Variables Check
echo -e "\n${YELLOW}Environment Variables:${NC}"
echo "---------------------"

# Check if .env files are gitignored
if [ -f ".gitignore" ]; then
    if grep -q "\.env" ".gitignore"; then
        echo -e "${GREEN}✓${NC} .env files are gitignored"
        ((PASSED_CHECKS++))
    else
        echo -e "${RED}✗${NC} .env files are NOT gitignored!"
        echo "   Add *.env to .gitignore immediately!"
    fi
else
    echo -e "${RED}✗${NC} No .gitignore file found"
fi
((TOTAL_CHECKS++))

# Summary
echo -e "\n${BLUE}Summary:${NC}"
echo "========"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC} / $TOTAL_CHECKS checks"

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    echo -e "\n${GREEN}✅ All checks passed! Ready for deployment.${NC}"
    echo -e "\nNext steps:"
    echo "1. Commit and push your changes"
    echo "2. Create staging branch: git checkout -b staging && git push -u origin staging"
    echo "3. Follow the deployment guide in DEPLOYMENT.md"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some checks failed. Please fix the issues above before deploying.${NC}"
    exit 1
fi