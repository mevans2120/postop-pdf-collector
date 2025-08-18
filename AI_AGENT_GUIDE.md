# AI Agent Guide for PostOp PDF Collector

## Overview

This guide enables AI agents (like Claude, GPT-4, or custom agents) to autonomously operate the PostOp PDF Collector system to gather, analyze, and manage post-operative instruction PDFs.

## Quick Setup for AI Agents

```bash
# 1. Clone and setup
git clone https://github.com/mevans2120/postop-pdf-collector.git
cd postop-pdf-collector

# 2. Run automated setup
./agent_setup.sh

# 3. Configure API keys (required for web search)
export GOOGLE_API_KEY="your_key_here"
export GOOGLE_SEARCH_ENGINE_ID="your_engine_id"

# 4. Start autonomous collection
./run_agent.sh autonomous 24  # Run for 24 hours
```

## Agent Capabilities

### 1. **Autonomous Collection**
The agent can run independently for extended periods:
```python
# Python interface
from agent_interface import AgentInterface

agent = AgentInterface()
result = await agent.run_autonomous_collection(
    duration_hours=48,
    interval_minutes=60
)
```

### 2. **Intelligent Search**
Automatically generates and optimizes search queries:
```python
# Agent determines best queries based on gaps
queries = agent.generate_search_queries(
    procedure_types=["cardiac", "orthopedic"]
)
```

### 3. **Quality Assessment**
Evaluates and filters PDFs by quality:
- Confidence scoring (0.0 - 1.0)
- Content completeness checks
- Relevance validation
- Duplicate detection

### 4. **Gap Analysis**
Identifies missing coverage and targets collection:
```python
analysis = agent.analyze_collection()
gaps = analysis["collection_gaps"]
# Agent automatically focuses on underrepresented areas
```

## Command-Line Interface

### Basic Commands

```bash
# Check system status
python agent_interface.py --action status

# Perform targeted collection
python agent_interface.py --action collect \
    --queries "knee surgery recovery pdf" \
    --max-pdfs 50

# Analyze current collection
python agent_interface.py --action analyze

# Search existing PDFs
python agent_interface.py --action search \
    --queries "cardiac medication"

# Run autonomous mode
python agent_interface.py --action autonomous \
    --duration 72  # hours
```

### Configuration File

Create `agent_config.json`:
```json
{
  "output_directory": "./pdfs",
  "max_pdfs_per_source": 10,
  "min_confidence_score": 0.7,
  "database_url": "sqlite:///./data/collector.db",
  "environment": "production"
}
```

Use with: `python agent_interface.py --config agent_config.json --action collect`

## Autonomous Operation Modes

### 1. **Aggressive Collection**
When PDF count is low (<100):
- Collects up to 100 PDFs per run
- Lower quality threshold (0.5)
- Parallel searches

### 2. **Quality Improvement**
When average confidence is low (<0.7):
- Focuses on high-quality sources
- Higher threshold (0.8)
- Verifies sources

### 3. **Targeted Collection**
When gaps are detected:
- Focuses on missing procedure types
- Balanced quality (0.7)
- Fills specific gaps

### 4. **Routine Collection**
Scheduled maintenance:
- Updates existing collection
- Moderate collection (20 PDFs)
- Maintains quality

## Decision Logic

The agent makes decisions based on:

```python
{
  "when_to_collect": [
    {"condition": "pdfs_count < 100", "action": "aggressive_collection"},
    {"condition": "average_confidence < 0.7", "action": "quality_improvement"},
    {"condition": "gaps_detected", "action": "targeted_collection"},
    {"condition": "scheduled_time", "action": "routine_collection"}
  ]
}
```

## API Integration

### Starting Collection via API

```python
import requests

# Start collection
response = requests.post(
    "http://localhost:8000/api/v1/collection/start",
    json={
        "search_queries": ["post op care pdf"],
        "max_pdfs": 50,
        "min_confidence": 0.6
    }
)
run_id = response.json()["run_id"]

# Check status
status = requests.get(
    f"http://localhost:8000/api/v1/collection/runs/{run_id}"
).json()
```

### Monitoring via API

```python
# Get statistics
stats = requests.get(
    "http://localhost:8000/api/v1/statistics/"
).json()

# Search PDFs
results = requests.post(
    "http://localhost:8000/api/v1/search/",
    json={"query": "knee surgery", "limit": 20}
).json()
```

## Scheduling and Automation

### Continuous Operation

```bash
# Run as daemon (background process)
./run_agent.sh daemon

# Check if running
ps aux | grep agent_interface

# Stop daemon
./run_agent.sh stop
```

### Cron Scheduling

Add to crontab for scheduled runs:
```cron
# Run daily at 2 AM
0 2 * * * cd /path/to/postop-pdf-collector && ./run_agent.sh collect

# Run weekly analysis
0 0 * * 0 cd /path/to/postop-pdf-collector && ./run_agent.sh analyze
```

### Systemd Service (Linux)

```bash
# Install as system service
sudo cp postop-agent.service /etc/systemd/system/
sudo systemctl enable postop-agent
sudo systemctl start postop-agent

# Check status
sudo systemctl status postop-agent
```

## Monitoring and Logs

### Log Files
- **Agent logs**: `./agent_logs/agent_YYYYMMDD_HHMMSS.log`
- **Collection history**: Stored in database
- **Metrics**: Available via API

### Real-time Monitoring

```bash
# Watch logs
tail -f agent_logs/agent_*.log

# Monitor with dashboard
python monitoring_dashboard.py
```

### Performance Metrics

The agent tracks:
- PDFs collected per run
- Success rates
- Average confidence scores
- Storage usage
- Collection gaps
- Source performance

## Best Practices for AI Agents

### 1. **Resource Management**
- Limit concurrent requests (2 per second default)
- Respect robots.txt
- Implement exponential backoff on failures

### 2. **Quality Control**
- Set minimum confidence threshold (0.6 recommended)
- Verify PDF content before storage
- Remove duplicates

### 3. **Storage Optimization**
- Clean up low-quality PDFs periodically
- Compress stored PDFs
- Monitor disk usage

### 4. **Error Handling**
```python
try:
    result = await agent.collect_pdfs()
except Exception as e:
    logger.error(f"Collection failed: {e}")
    # Agent continues with next task
```

## Integration Examples

### For Claude/Anthropic Agents

```python
# Claude can use this interface
import asyncio
from agent_interface import AgentInterface

async def claude_collect():
    agent = AgentInterface({
        "min_confidence_score": 0.7,
        "max_pdfs_per_source": 10
    })
    
    # Analyze what's needed
    analysis = agent.analyze_collection()
    
    # Make intelligent decision
    if analysis["total_pdfs"] < 100:
        # Need more PDFs
        result = await agent.collect_pdfs(max_pdfs=50)
    elif analysis["average_confidence"] < 0.7:
        # Need better quality
        result = await agent.collect_pdfs(quality_threshold=0.8)
    else:
        # Routine collection
        result = await agent.collect_pdfs(max_pdfs=20)
    
    return result

# Run
asyncio.run(claude_collect())
```

### For GPT-4/OpenAI Agents

```python
# GPT-4 function calling interface
functions = [
    {
        "name": "collect_pdfs",
        "parameters": {
            "search_queries": ["array", "of", "queries"],
            "max_pdfs": 50,
            "quality_threshold": 0.7
        }
    },
    {
        "name": "analyze_collection",
        "parameters": {}
    },
    {
        "name": "search_pdfs",
        "parameters": {
            "query": "search term",
            "procedure_type": "optional filter"
        }
    }
]
```

### For Custom Agents

```python
class CustomAgent:
    def __init__(self):
        self.collector = AgentInterface()
    
    async def run(self):
        while True:
            # Custom logic
            status = self.collector.get_status()
            
            if self.should_collect(status):
                await self.collector.collect_pdfs()
            
            await asyncio.sleep(3600)  # Wait 1 hour
```

## Troubleshooting

### Common Issues

1. **No PDFs collected**
   - Check API keys are set
   - Verify internet connection
   - Check logs for errors

2. **Low quality PDFs**
   - Increase `min_confidence_score`
   - Target specific reputable sources
   - Update search queries

3. **Database errors**
   - Run: `python -c "from postop_collector.storage.database import init_database, create_database_engine; engine = create_database_engine(); init_database(engine)"`

4. **Memory issues**
   - Reduce `max_pdfs_per_source`
   - Implement cleanup policy
   - Use PostgreSQL instead of SQLite

## Environment Variables

```bash
# Required for web search
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_engine_id"

# Optional configuration
export DATABASE_URL="postgresql://user:pass@localhost/postop"
export LOG_LEVEL="INFO"
export OUTPUT_DIRECTORY="./pdfs"
export MAX_PDFS_PER_SOURCE="10"
export MIN_CONFIDENCE_SCORE="0.6"
```

## Support and Updates

- **Repository**: https://github.com/mevans2120/postop-pdf-collector
- **Issues**: https://github.com/mevans2120/postop-pdf-collector/issues
- **API Docs**: See API_DOCUMENTATION.md

## Summary

The AI Agent Interface provides:
- ✅ Fully autonomous operation
- ✅ Intelligent decision making
- ✅ Quality control
- ✅ Gap analysis
- ✅ Scheduled operations
- ✅ API integration
- ✅ Monitoring and logging
- ✅ Error recovery

Perfect for AI agents to operate independently and maintain a high-quality collection of post-operative instruction PDFs.