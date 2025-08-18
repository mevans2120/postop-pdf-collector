#!/bin/bash

# Setup script for AI Agent to run PostOp PDF Collector

set -e

echo "=========================================="
echo "PostOp PDF Collector - AI Agent Setup"
echo "=========================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to setup Python environment
setup_python() {
    echo "Setting up Python environment..."
    
    # Check Python version
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        echo "✓ Python $PYTHON_VERSION found"
    else
        echo "❌ Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
}

# Function to setup database
setup_database() {
    echo "Setting up database..."
    
    # Create data directory
    mkdir -p data
    
    # Initialize database
    python3 -c "
from postop_collector.storage.database import init_database, create_database_engine
engine = create_database_engine()
init_database(engine)
print('✓ Database initialized')
"
}

# Function to setup API keys
setup_api_keys() {
    echo "Setting up API keys..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "⚠️  Created .env file from template"
        echo "   Please edit .env and add your API keys:"
        echo "   - GOOGLE_API_KEY"
        echo "   - GOOGLE_SEARCH_ENGINE_ID"
    else
        echo "✓ .env file exists"
    fi
    
    # Check if API keys are set
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "⚠️  GOOGLE_API_KEY not set in environment"
    fi
}

# Function to create agent directories
setup_directories() {
    echo "Creating agent directories..."
    mkdir -p agent_output
    mkdir -p agent_logs
    mkdir -p data
    echo "✓ Directories created"
}

# Function to test agent
test_agent() {
    echo "Testing agent interface..."
    
    # Test status command
    python3 agent_interface.py --action status
    
    if [ $? -eq 0 ]; then
        echo "✓ Agent interface working"
    else
        echo "❌ Agent interface test failed"
        exit 1
    fi
}

# Function to setup systemd service (Linux only)
setup_service() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Setting up systemd service..."
        
        cat > postop-agent.service <<EOF
[Unit]
Description=PostOp PDF Collector Agent
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$(pwd)/venv/bin/python $(pwd)/agent_interface.py --action autonomous --duration 720
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF
        
        echo "Service file created: postop-agent.service"
        echo "To install:"
        echo "  sudo cp postop-agent.service /etc/systemd/system/"
        echo "  sudo systemctl daemon-reload"
        echo "  sudo systemctl enable postop-agent"
        echo "  sudo systemctl start postop-agent"
    fi
}

# Function to create agent runner script
create_runner() {
    cat > run_agent.sh <<'EOF'
#!/bin/bash

# Runner script for PostOp PDF Collector Agent

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Parse arguments
ACTION=${1:-autonomous}
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
        echo "Usage: ./run_agent.sh [collect|analyze|search|status|autonomous|daemon|stop] [duration]"
        exit 1
        ;;
esac
EOF
    
    chmod +x run_agent.sh
    echo "✓ Agent runner script created: run_agent.sh"
}

# Main setup flow
main() {
    echo ""
    echo "1. CHECKING PREREQUISITES"
    echo "-" * 40
    
    # Check Docker (optional)
    if command_exists docker; then
        echo "✓ Docker found (optional)"
    else
        echo "⚠️  Docker not found (optional for containerized deployment)"
    fi
    
    echo ""
    echo "2. SETTING UP ENVIRONMENT"
    echo "-" * 40
    setup_python
    
    echo ""
    echo "3. SETTING UP DATABASE"
    echo "-" * 40
    setup_database
    
    echo ""
    echo "4. SETTING UP DIRECTORIES"
    echo "-" * 40
    setup_directories
    
    echo ""
    echo "5. SETTING UP API KEYS"
    echo "-" * 40
    setup_api_keys
    
    echo ""
    echo "6. CREATING RUNNER SCRIPTS"
    echo "-" * 40
    create_runner
    setup_service
    
    echo ""
    echo "7. TESTING AGENT"
    echo "-" * 40
    test_agent
    
    echo ""
    echo "=========================================="
    echo "✅ AI Agent Setup Complete!"
    echo "=========================================="
    echo ""
    echo "QUICK START:"
    echo "------------"
    echo "1. Edit .env file with your API keys"
    echo "2. Run agent in different modes:"
    echo ""
    echo "   Status check:"
    echo "   ./run_agent.sh status"
    echo ""
    echo "   Single collection:"
    echo "   ./run_agent.sh collect"
    echo ""
    echo "   Autonomous mode (24 hours):"
    echo "   ./run_agent.sh autonomous 24"
    echo ""
    echo "   Background daemon (30 days):"
    echo "   ./run_agent.sh daemon"
    echo ""
    echo "   Stop daemon:"
    echo "   ./run_agent.sh stop"
    echo ""
    echo "AGENT CAPABILITIES:"
    echo "-------------------"
    echo "• Autonomous PDF collection"
    echo "• Intelligent search query generation"
    echo "• Quality assessment and filtering"
    echo "• Gap analysis and targeted collection"
    echo "• Scheduled operations"
    echo "• Self-monitoring and reporting"
    echo ""
    echo "MONITORING:"
    echo "-----------"
    echo "• Logs: ./agent_logs/"
    echo "• Output: ./agent_output/"
    echo "• Database: ./data/agent_collector.db"
    echo ""
}

# Run main setup
main