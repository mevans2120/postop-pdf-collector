"""Monitoring and metrics endpoints."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

from postop_collector.monitoring.metrics import get_metrics
from postop_collector.monitoring.prometheus import get_prometheus_metrics

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> Response:
    """Expose metrics in Prometheus format."""
    metrics_data = get_prometheus_metrics()
    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@router.get("/metrics/json")
async def json_metrics():
    """Get metrics in JSON format."""
    return get_metrics()


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(request: Request):
    """Kubernetes readiness probe."""
    # Check if database is accessible
    try:
        db = request.app.state.db
        stats = db.get_statistics()
        db_ready = stats is not None
    except Exception:
        db_ready = False
    
    if db_ready:
        return {"status": "ready", "database": "connected"}
    else:
        return Response(
            content='{"status": "not ready", "database": "disconnected"}',
            status_code=503
        )