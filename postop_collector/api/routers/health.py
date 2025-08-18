"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter, Request

from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Check API health status."""
    # Check database connection
    db_connected = False
    try:
        if hasattr(request.app.state, "db"):
            stats = request.app.state.db.get_statistics()
            db_connected = stats is not None
    except Exception:
        db_connected = False
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database_connected=db_connected,
        timestamp=datetime.utcnow()
    )


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PostOp PDF Collector API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }