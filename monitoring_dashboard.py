#!/usr/bin/env python3
"""Real-time monitoring dashboard for PostOp PDF Collector."""

import time
import sys
import os
import requests
import curses
from datetime import datetime
from typing import Dict, Any


class MonitoringDashboard:
    """Terminal-based monitoring dashboard."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """Initialize dashboard.
        
        Args:
            api_url: Base URL of the API
        """
        self.api_url = api_url
        self.refresh_interval = 2  # seconds
        self.running = True
    
    def fetch_metrics(self) -> Dict[str, Any]:
        """Fetch current metrics from API."""
        try:
            # Get statistics
            stats_response = requests.get(f"{self.api_url}/api/v1/statistics/")
            stats = stats_response.json() if stats_response.ok else {}
            
            # Get health status
            health_response = requests.get(f"{self.api_url}/health")
            health = health_response.json() if health_response.ok else {}
            
            # Get active collections
            collections_response = requests.get(f"{self.api_url}/api/v1/collection/active")
            collections = collections_response.json() if collections_response.ok else {}
            
            # Get JSON metrics
            metrics_response = requests.get(f"{self.api_url}/monitoring/metrics/json")
            metrics = metrics_response.json() if metrics_response.ok else {}
            
            return {
                "stats": stats,
                "health": health,
                "collections": collections,
                "metrics": metrics,
                "timestamp": datetime.now()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def draw_dashboard(self, stdscr, data: Dict[str, Any]):
        """Draw dashboard on screen."""
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Title
        title = "PostOp PDF Collector - Monitoring Dashboard"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        stdscr.addstr(1, 0, "=" * width)
        
        row = 3
        
        # Timestamp
        timestamp = data.get("timestamp", datetime.now())
        stdscr.addstr(row, 0, f"Last Updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        row += 2
        
        # Error display
        if "error" in data:
            stdscr.addstr(row, 0, f"Error: {data['error']}", curses.A_BOLD | curses.color_pair(1))
            row += 2
            return
        
        # Health Status
        health = data.get("health", {})
        status = health.get("status", "unknown")
        db_connected = health.get("database_connected", False)
        
        stdscr.addstr(row, 0, "System Health", curses.A_BOLD)
        row += 1
        
        status_color = curses.color_pair(2) if status == "healthy" else curses.color_pair(1)
        stdscr.addstr(row, 2, f"API Status: {status}", status_color)
        row += 1
        
        db_color = curses.color_pair(2) if db_connected else curses.color_pair(1)
        stdscr.addstr(row, 2, f"Database: {'Connected' if db_connected else 'Disconnected'}", db_color)
        row += 2
        
        # Statistics
        stats = data.get("stats", {})
        if stats:
            stdscr.addstr(row, 0, "Statistics", curses.A_BOLD)
            row += 1
            
            stdscr.addstr(row, 2, f"Total PDFs: {stats.get('total_pdfs', 0)}")
            row += 1
            stdscr.addstr(row, 2, f"Collection Runs: {stats.get('total_collection_runs', 0)}")
            row += 1
            stdscr.addstr(row, 2, f"Average Confidence: {stats.get('average_confidence', 0):.2%}")
            row += 1
            stdscr.addstr(row, 2, f"Storage Used: {stats.get('total_storage_mb', 0):.2f} MB")
            row += 2
        
        # Active Collections
        collections = data.get("collections", {}).get("active_collections", [])
        stdscr.addstr(row, 0, "Active Collections", curses.A_BOLD)
        row += 1
        
        if collections:
            for collection in collections[:5]:  # Show max 5
                stdscr.addstr(row, 2, f"• {collection['run_id'][:8]}... - {collection['status']}")
                row += 1
        else:
            stdscr.addstr(row, 2, "No active collections")
            row += 1
        row += 1
        
        # Metrics
        metrics = data.get("metrics", {})
        if metrics:
            stdscr.addstr(row, 0, "Performance Metrics", curses.A_BOLD)
            row += 1
            
            # Counters
            counters = metrics.get("counters", {})
            if counters:
                for key, value in list(counters.items())[:5]:
                    stdscr.addstr(row, 2, f"{key}: {value}")
                    row += 1
            
            row += 1
            
            # Gauges
            gauges = metrics.get("gauges", {})
            if gauges:
                stdscr.addstr(row, 0, "Current Values", curses.A_BOLD)
                row += 1
                for key, value in list(gauges.items())[:5]:
                    stdscr.addstr(row, 2, f"{key}: {value:.2f}")
                    row += 1
        
        # Footer
        footer = "Press 'q' to quit, 'r' to refresh"
        stdscr.addstr(height - 2, 0, "=" * width)
        stdscr.addstr(height - 1, (width - len(footer)) // 2, footer)
        
        stdscr.refresh()
    
    def run(self, stdscr):
        """Run the dashboard."""
        # Setup colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)    # Error
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Warning
        
        # Set non-blocking input
        stdscr.nodelay(True)
        
        last_update = 0
        data = {}
        
        while self.running:
            # Check for input
            try:
                key = stdscr.getkey()
                if key == 'q':
                    self.running = False
                elif key == 'r':
                    last_update = 0  # Force refresh
            except:
                pass
            
            # Update data if needed
            current_time = time.time()
            if current_time - last_update > self.refresh_interval:
                data = self.fetch_metrics()
                last_update = current_time
            
            # Draw dashboard
            if data:
                self.draw_dashboard(stdscr, data)
            
            # Small delay to prevent CPU spinning
            time.sleep(0.1)


def main():
    """Run the monitoring dashboard."""
    print("Starting PostOp PDF Collector Monitoring Dashboard...")
    print("Connecting to API at http://localhost:8000")
    print()
    
    # Check if API is accessible
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if not response.ok:
            print("⚠️  Warning: API returned status code", response.status_code)
    except requests.exceptions.RequestException as e:
        print("❌ Error: Cannot connect to API")
        print(f"   Make sure the API is running: python run_api.py")
        print(f"   Error: {e}")
        return 1
    
    # Run dashboard
    dashboard = MonitoringDashboard()
    
    try:
        curses.wrapper(dashboard.run)
    except KeyboardInterrupt:
        pass
    
    print("\nDashboard stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())