#!/bin/bash

# Runner script for PostOp PDF Collector Agent

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Parse arguments
ACTION=${1:-status}
DURATION=${2:-24}

echo "Starting agent in $ACTION mode..."

case "$ACTION" in
    collect)
        python3 agent_interface.py --action collect \
            --queries "post operative care pdf" "surgery recovery pdf" \
            --max-pdfs 50
        ;;
    
    analyze)
        python3 agent_interface.py --action analyze
        ;;
    
    search)
        python3 agent_interface.py --action search --queries "$3"
        ;;
    
    status)
        python3 agent_interface.py --action status
        ;;
    
    autonomous)
        python3 agent_interface.py --action autonomous --duration $DURATION
        ;;
    
    api)
        echo "Starting API server..."
        python3 run_api.py
        ;;
    
    daemon)
        # Run in background with logging
        nohup python3 agent_interface.py --action autonomous --duration 720 \
            > agent_logs/daemon.log 2>&1 &
        echo $! > agent.pid
        echo "Agent started with PID: $(cat agent.pid)"
        ;;
    
    stop)
        if [ -f agent.pid ]; then
            kill $(cat agent.pid)
            rm agent.pid
            echo "Agent stopped"
        else
            echo "No agent running"
        fi
        ;;
    
    *)
        echo "Usage: ./run_agent.sh [collect|analyze|search|status|autonomous|api|daemon|stop] [duration]"
        echo ""
        echo "Examples:"
        echo "  ./run_agent.sh status           # Check system status"
        echo "  ./run_agent.sh collect          # Collect PDFs once"
        echo "  ./run_agent.sh autonomous 24    # Run autonomously for 24 hours"
        echo "  ./run_agent.sh api              # Start REST API server"
        echo "  ./run_agent.sh daemon           # Run as background daemon"
        echo "  ./run_agent.sh stop             # Stop background daemon"
        exit 1
        ;;
esac