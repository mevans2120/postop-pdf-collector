#!/bin/bash

# PostOp PDF Collector Deployment Script

set -e

echo "=========================================="
echo "PostOp PDF Collector Deployment"
echo "=========================================="

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Parse arguments
ENVIRONMENT=${1:-production}
ACTION=${2:-up}

echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"

# Load environment variables
if [ -f ".env.$ENVIRONMENT" ]; then
    echo "Loading environment from .env.$ENVIRONMENT"
    export $(cat .env.$ENVIRONMENT | grep -v '^#' | xargs)
elif [ -f ".env" ]; then
    echo "Loading environment from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: No environment file found"
fi

# Create necessary directories
mkdir -p data output logs

case "$ACTION" in
    up|start)
        echo "Starting services..."
        docker-compose up -d
        echo "Services started successfully!"
        echo "API available at: http://localhost:8000"
        echo "Documentation at: http://localhost:8000/docs"
        ;;
    
    down|stop)
        echo "Stopping services..."
        docker-compose down
        echo "Services stopped."
        ;;
    
    restart)
        echo "Restarting services..."
        docker-compose restart
        echo "Services restarted."
        ;;
    
    build)
        echo "Building Docker images..."
        docker-compose build --no-cache
        echo "Build completed."
        ;;
    
    logs)
        echo "Showing logs..."
        docker-compose logs -f
        ;;
    
    status)
        echo "Service status:"
        docker-compose ps
        ;;
    
    backup)
        echo "Creating database backup..."
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        docker-compose exec postgres pg_dump -U postop postop_collector > "data/$BACKUP_FILE"
        echo "Backup saved to data/$BACKUP_FILE"
        ;;
    
    restore)
        if [ -z "$3" ]; then
            echo "Usage: ./deploy.sh $ENVIRONMENT restore <backup_file>"
            exit 1
        fi
        echo "Restoring database from $3..."
        docker-compose exec -T postgres psql -U postop postop_collector < "$3"
        echo "Database restored."
        ;;
    
    migrate)
        echo "Running database migrations..."
        docker-compose exec api python -c "
from postop_collector.storage.database import init_database, create_database_engine
engine = create_database_engine()
init_database(engine)
print('Database migrations completed.')
"
        ;;
    
    test)
        echo "Running tests..."
        docker-compose exec api pytest tests/
        ;;
    
    shell)
        echo "Opening shell in API container..."
        docker-compose exec api /bin/bash
        ;;
    
    clean)
        echo "Cleaning up..."
        docker-compose down -v
        docker system prune -f
        echo "Cleanup completed."
        ;;
    
    *)
        echo "Usage: ./deploy.sh [environment] [action]"
        echo ""
        echo "Environments:"
        echo "  development   - Local development"
        echo "  production    - Production deployment"
        echo ""
        echo "Actions:"
        echo "  up/start      - Start all services"
        echo "  down/stop     - Stop all services"
        echo "  restart       - Restart all services"
        echo "  build         - Build Docker images"
        echo "  logs          - Show service logs"
        echo "  status        - Show service status"
        echo "  backup        - Backup database"
        echo "  restore <file> - Restore database from backup"
        echo "  migrate       - Run database migrations"
        echo "  test          - Run tests"
        echo "  shell         - Open shell in API container"
        echo "  clean         - Clean up containers and volumes"
        exit 1
        ;;
esac

echo "=========================================="
echo "Operation completed successfully!"
echo "==========================================="