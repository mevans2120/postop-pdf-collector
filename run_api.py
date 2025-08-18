#!/usr/bin/env python3
"""Run the PostOp PDF Collector REST API."""

import os
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

from postop_collector.api import create_app
from postop_collector.config.settings import get_settings


def main():
    """Run the API server."""
    # Get settings
    settings = get_settings()
    
    # Create app
    app = create_app(settings)
    
    # Get host and port from environment or use defaults
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("ENVIRONMENT", "development") == "development"
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║         PostOp PDF Collector REST API                       ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Starting server at: http://{host}:{port}                      ║
    ║  API Documentation: http://localhost:{port}/docs               ║
    ║  Alternative docs: http://localhost:{port}/redoc              ║
    ║  Health check: http://localhost:{port}/health                 ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Environment: {settings.environment}
    Database: {settings.database_url or 'SQLite (default)'}
    Log Level: {settings.log_level}
    
    Press CTRL+C to stop the server.
    """)
    
    # Run server
    if reload:
        # Use module string for reload
        uvicorn.run(
            "postop_collector.api:create_app",
            host=host,
            port=port,
            reload=True,
            log_level=settings.log_level.lower(),
            factory=True,
        )
    else:
        # Use app instance for production
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level=settings.log_level.lower(),
        )


if __name__ == "__main__":
    main()