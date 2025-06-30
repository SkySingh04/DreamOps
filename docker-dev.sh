#!/bin/bash

# Docker Compose development helper script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if .env file exists in backend
if [ ! -f backend/.env.local ]; then
    print_warning "backend/.env.local not found. Copying from .env.example..."
    cp backend/.env.example backend/.env.local
    print_error "Please edit backend/.env.local with your API keys!"
    exit 1
fi

# Check if .env file exists in frontend
if [ ! -f frontend/.env.local ]; then
    print_warning "frontend/.env.local not found. Copying from .env.example..."
    cp frontend/.env.example frontend/.env.local
    print_warning "Using default PostgreSQL connection for Docker Compose"
fi

# Check for required environment variables
if ! grep -q "ANTHROPIC_API_KEY=" backend/.env.local || grep -q "ANTHROPIC_API_KEY=your-anthropic-api-key" backend/.env.local; then
    print_error "Please set ANTHROPIC_API_KEY in backend/.env.local"
    exit 1
fi

# Export environment variables for docker-compose
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY backend/.env.local | cut -d '=' -f2)

case "$1" in
    up)
        print_status "Starting all services..."
        docker-compose up -d
        print_status "Waiting for services to be ready..."
        sleep 10
        print_status "Running database migrations..."
        docker-compose exec frontend npm run db:migrate:local
        print_status "All services are running!"
        print_status "Frontend: http://localhost:3000"
        print_status "Backend API: http://localhost:8000"
        print_status "API Docs: http://localhost:8000/docs"
        print_status "PostgreSQL: localhost:5432"
        ;;
    down)
        print_status "Stopping all services..."
        docker-compose down
        ;;
    restart)
        print_status "Restarting all services..."
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f ${2:-}
        ;;
    build)
        print_status "Building Docker images..."
        docker-compose build
        ;;
    rebuild)
        print_status "Rebuilding Docker images from scratch..."
        docker-compose build --no-cache
        ;;
    db)
        print_status "Accessing PostgreSQL database..."
        docker-compose exec postgres psql -U oncall_user -d oncall_agent
        ;;
    migrate)
        print_status "Running database migrations..."
        docker-compose exec frontend npm run db:migrate:local
        ;;
    studio)
        print_status "Opening Drizzle Studio..."
        docker-compose exec frontend npm run db:studio
        ;;
    shell)
        service=${2:-backend}
        print_status "Opening shell in $service container..."
        docker-compose exec $service /bin/sh
        ;;
    *)
        echo "Usage: $0 {up|down|restart|logs|build|rebuild|db|migrate|studio|shell}"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services"
        echo "  down     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show logs (optionally specify service: logs backend)"
        echo "  build    - Build Docker images"
        echo "  rebuild  - Rebuild Docker images from scratch"
        echo "  db       - Access PostgreSQL database"
        echo "  migrate  - Run database migrations"
        echo "  studio   - Open Drizzle Studio"
        echo "  shell    - Open shell in container (default: backend, or specify: shell frontend)"
        exit 1
        ;;
esac