#!/bin/bash

# Docker setup verification script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_test() {
    echo -e "\n${BLUE}Testing:${NC} $1"
}

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to check if a command succeeds
check_command() {
    if eval "$1" > /dev/null 2>&1; then
        print_status "$2"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "$2"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local description=$2
    local expected_status=${3:-200}
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        print_status "$description (HTTP $response)"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "$description (HTTP $response, expected $expected_status)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check JSON response
check_json_endpoint() {
    local url=$1
    local description=$2
    local json_path=$3
    local expected_value=$4
    
    response=$(curl -s "$url" 2>/dev/null)
    if [ $? -ne 0 ]; then
        print_error "$description - Failed to connect"
        ((TESTS_FAILED++))
        return 1
    fi
    
    # Check if response is valid JSON
    if ! echo "$response" | jq . >/dev/null 2>&1; then
        print_error "$description - Invalid JSON response"
        ((TESTS_FAILED++))
        return 1
    fi
    
    # Check specific value if provided
    if [ -n "$json_path" ]; then
        actual_value=$(echo "$response" | jq -r "$json_path" 2>/dev/null)
        if [ "$actual_value" = "$expected_value" ]; then
            print_status "$description ($json_path = $actual_value)"
            ((TESTS_PASSED++))
            return 0
        else
            print_error "$description ($json_path = $actual_value, expected $expected_value)"
            ((TESTS_FAILED++))
            return 1
        fi
    else
        print_status "$description"
        ((TESTS_PASSED++))
        return 0
    fi
}

echo "======================================"
echo "Docker Setup Verification Test Suite"
echo "======================================"

# 1. Check Docker and Docker Compose
print_test "Docker Installation"
check_command "docker --version" "Docker is installed"
check_command "docker-compose --version" "Docker Compose is installed"

# 2. Check if containers are running
print_test "Container Status"
check_command "docker-compose ps | grep -q 'oncall-agent-backend.*Up'" "Backend container is running"
check_command "docker-compose ps | grep -q 'oncall-agent-frontend.*Up'" "Frontend container is running"
check_command "docker-compose ps | grep -q 'oncall-agent-db.*Up'" "PostgreSQL container is running"
check_command "docker-compose ps | grep -q 'oncall-agent-redis.*Up'" "Redis container is running"

# 3. Check backend API endpoints
print_test "Backend API Health"
sleep 5  # Give services time to fully start

check_endpoint "http://localhost:8000" "Backend root endpoint"
check_endpoint "http://localhost:8000/health" "Backend health endpoint"
check_endpoint "http://localhost:8000/docs" "Backend API documentation (Swagger)"
check_endpoint "http://localhost:8000/redoc" "Backend API documentation (ReDoc)"

# 4. Check backend API responses
print_test "Backend API Responses"
check_json_endpoint "http://localhost:8000/health" "Health check response" ".status" "healthy"
check_json_endpoint "http://localhost:8000" "Root endpoint response" ".service" "Oncall Agent API"

# 5. Check frontend
print_test "Frontend Application"
check_endpoint "http://localhost:3000" "Frontend application"

# 6. Check database connectivity
print_test "Database Connectivity"
if docker-compose exec -T postgres psql -U oncall_user -d oncall_agent -c "SELECT 1;" > /dev/null 2>&1; then
    print_status "PostgreSQL is accessible"
    ((TESTS_PASSED++))
else
    print_error "PostgreSQL is not accessible"
    ((TESTS_FAILED++))
fi

# 7. Check Redis connectivity
print_test "Redis Connectivity"
if docker-compose exec -T redis redis-cli ping | grep -q "PONG" 2>/dev/null; then
    print_status "Redis is accessible"
    ((TESTS_PASSED++))
else
    print_error "Redis is not accessible"
    ((TESTS_FAILED++))
fi

# 8. Check environment variables
print_test "Environment Configuration"

# Check dev mode in backend
dev_mode_response=$(curl -s "http://localhost:8000/api/v1/alert-tracking/usage/test-user" 2>/dev/null)
if echo "$dev_mode_response" | jq -r '.account_tier' | grep -q "pro"; then
    print_status "Backend is in development mode (auto-pro plan enabled)"
    ((TESTS_PASSED++))
else
    print_error "Backend development mode not working correctly"
    ((TESTS_FAILED++))
fi

# 9. Check CORS configuration
print_test "CORS Configuration"
cors_response=$(curl -s -I -X OPTIONS http://localhost:8000/api/v1/alerts \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST" 2>/dev/null | grep -i "access-control-allow-origin")

if echo "$cors_response" | grep -q "http://localhost:3000"; then
    print_status "CORS is properly configured"
    ((TESTS_PASSED++))
else
    print_error "CORS is not properly configured"
    ((TESTS_FAILED++))
fi

# 10. Check volume mounts
print_test "Volume Mounts"
if docker-compose exec -T backend ls /app/src/oncall_agent > /dev/null 2>&1; then
    print_status "Backend volume mount is working"
    ((TESTS_PASSED++))
else
    print_error "Backend volume mount is not working"
    ((TESTS_FAILED++))
fi

if docker-compose exec -T frontend ls /app/app > /dev/null 2>&1; then
    print_status "Frontend volume mount is working"
    ((TESTS_PASSED++))
else
    print_error "Frontend volume mount is not working"
    ((TESTS_FAILED++))
fi

# 11. Check mock payments
print_test "Mock Payment System"
check_json_endpoint "http://localhost:8000/api/v1/payments/debug/environment" "Payment environment check" ".mock_payments_enabled" "true"

# 12. Check integrations
print_test "Integration Endpoints"
check_endpoint "http://localhost:8000/api/v1/integrations" "Integrations list endpoint"
check_endpoint "http://localhost:8000/api/v1/alert-tracking/plans" "Payment plans endpoint"

# Print summary
echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! Your Docker setup is working correctly.${NC}"
    echo ""
    echo "You can now access:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Database: localhost:5432 (user: oncall_user, password: changeme)"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the error messages above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Make sure all containers are running: docker-compose ps"
    echo "  - Check container logs: docker-compose logs [service-name]"
    echo "  - Ensure ports 3000, 8000, 5432, 6379 are not in use"
    echo "  - Try rebuilding: ./docker-dev.sh rebuild"
    exit 1
fi