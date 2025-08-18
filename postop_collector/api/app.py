"""FastAPI application factory and configuration."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from postop_collector.config.settings import Settings
from postop_collector.storage.metadata_db import MetadataDB

from .middleware import LoggingMiddleware, RateLimitMiddleware
from .routers import collection, health, pdfs, search, statistics, monitoring

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting PostOp PDF Collector API")
    
    # Initialize database
    settings = app.state.settings
    app.state.db = MetadataDB(
        database_url=settings.database_url,
        environment=settings.environment
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down PostOp PDF Collector API")
    if hasattr(app.state, "db"):
        app.state.db.close()


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Create and configure FastAPI application.
    
    Args:
        settings: Optional settings object
        
    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = Settings()
    
    app = FastAPI(
        title="PostOp PDF Collector API",
        description="REST API for collecting and analyzing post-operative instruction PDFs",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Store settings in app state
    app.state.settings = settings
    
    # Configure middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=100, window=60)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(pdfs.router, prefix="/api/v1/pdfs", tags=["pdfs"])
    app.include_router(collection.router, prefix="/api/v1/collection", tags=["collection"])
    app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
    app.include_router(statistics.router, prefix="/api/v1/statistics", tags=["statistics"])
    app.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
    
    return app