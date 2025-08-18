#!/bin/bash

# Setup monitoring for PostOp PDF Collector

set -e

echo "=========================================="
echo "PostOp PDF Collector - Monitoring Setup"
echo "=========================================="

# Create required directories
echo "Creating monitoring directories..."
mkdir -p logs metrics profiles

# Install monitoring dependencies
echo "Installing monitoring dependencies..."
pip3 install prometheus-client psutil

# Setup Prometheus (if docker is available)
if command -v docker >/dev/null 2>&1; then
    echo "Setting up Prometheus..."
    
    # Create Prometheus config
    cat > prometheus.yml <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'postop-collector'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/monitoring/metrics'
EOF
    
    echo "Prometheus configuration created."
    echo "To start Prometheus, run:"
    echo "  docker run -d -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus"
fi

# Setup Grafana (optional)
echo ""
echo "To setup Grafana for visualization:"
echo "1. Run: docker run -d -p 3000:3000 grafana/grafana"
echo "2. Access Grafana at http://localhost:3000 (admin/admin)"
echo "3. Add Prometheus data source: http://host.docker.internal:9090"
echo "4. Import dashboard from grafana_dashboard.json"

# Create Grafana dashboard JSON
cat > grafana_dashboard.json <<'EOF'
{
  "dashboard": {
    "title": "PostOp PDF Collector",
    "panels": [
      {
        "title": "PDFs Collected",
        "targets": [
          {
            "expr": "rate(postop_pdf_collected_total[5m])"
          }
        ]
      },
      {
        "title": "API Request Rate",
        "targets": [
          {
            "expr": "rate(postop_api_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Collection Success Rate",
        "targets": [
          {
            "expr": "rate(postop_pdf_collected_total[1h]) / (rate(postop_pdf_collected_total[1h]) + rate(postop_pdf_collection_errors_total[1h]))"
          }
        ]
      },
      {
        "title": "API Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(postop_api_request_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
EOF

# Create systemd service file (for Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Creating systemd service file..."
    cat > postop-collector.service <<EOF
[Unit]
Description=PostOp PDF Collector API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="ENVIRONMENT=production"
ExecStart=/usr/bin/python3 $(pwd)/run_api.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    echo "Systemd service file created."
    echo "To install as a service:"
    echo "  sudo cp postop-collector.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable postop-collector"
    echo "  sudo systemctl start postop-collector"
fi

# Create log rotation config
echo "Creating log rotation configuration..."
cat > logrotate.conf <<EOF
$(pwd)/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $USER $USER
    sharedscripts
    postrotate
        # Send signal to reload logs if needed
        killall -USR1 python3 2>/dev/null || true
    endscript
}
EOF

echo "Log rotation configuration created."
echo "To enable log rotation:"
echo "  sudo cp logrotate.conf /etc/logrotate.d/postop-collector"

# Create monitoring check script
cat > check_health.sh <<'EOF'
#!/bin/bash
# Health check script for monitoring tools

API_URL="${API_URL:-http://localhost:8000}"

# Check API health
health_response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/health)
if [ "$health_response" != "200" ]; then
    echo "CRITICAL: API health check failed (HTTP $health_response)"
    exit 2
fi

# Check database
db_check=$(curl -s $API_URL/monitoring/health/ready | jq -r '.database')
if [ "$db_check" != "connected" ]; then
    echo "WARNING: Database not connected"
    exit 1
fi

echo "OK: All systems operational"
exit 0
EOF
chmod +x check_health.sh

echo ""
echo "=========================================="
echo "Monitoring Setup Complete!"
echo "=========================================="
echo ""
echo "Available monitoring endpoints:"
echo "  - Prometheus metrics: http://localhost:8000/monitoring/metrics"
echo "  - JSON metrics: http://localhost:8000/monitoring/metrics/json"
echo "  - Health check: http://localhost:8000/health"
echo "  - Liveness probe: http://localhost:8000/monitoring/health/live"
echo "  - Readiness probe: http://localhost:8000/monitoring/health/ready"
echo ""
echo "To start monitoring dashboard:"
echo "  python3 monitoring_dashboard.py"
echo ""
echo "To check system health:"
echo "  ./check_health.sh"
echo ""
echo "Logs are stored in: ./logs/"
echo "Metrics are stored in: ./metrics/"
echo ""