"""Prometheus metrics exporter."""

from typing import Dict, Any, Optional
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.core import REGISTRY


# Define metrics
pdf_collected_total = Counter(
    "postop_pdf_collected_total",
    "Total number of PDFs collected",
    ["source", "procedure_type", "quality"]
)

pdf_collection_errors_total = Counter(
    "postop_pdf_collection_errors_total",
    "Total number of PDF collection errors",
    ["error_type", "source"]
)

collection_duration_seconds = Histogram(
    "postop_collection_duration_seconds",
    "Duration of collection runs in seconds",
    ["status"]
)

api_requests_total = Counter(
    "postop_api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status"]
)

api_request_duration_seconds = Histogram(
    "postop_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

database_operations_total = Counter(
    "postop_database_operations_total",
    "Total number of database operations",
    ["operation", "table", "status"]
)

database_operation_duration_seconds = Histogram(
    "postop_database_operation_duration_seconds",
    "Database operation duration in seconds",
    ["operation", "table"]
)

active_collections = Gauge(
    "postop_active_collections",
    "Number of active collection runs"
)

pdf_storage_bytes = Gauge(
    "postop_pdf_storage_bytes",
    "Total storage used for PDFs in bytes"
)

pdf_confidence_score = Summary(
    "postop_pdf_confidence_score",
    "PDF confidence scores",
    ["procedure_type"]
)

analysis_processing_time_seconds = Histogram(
    "postop_analysis_processing_time_seconds",
    "PDF analysis processing time in seconds",
    ["analysis_type"]
)

cache_hits_total = Counter(
    "postop_cache_hits_total",
    "Total number of cache hits",
    ["cache_type"]
)

cache_misses_total = Counter(
    "postop_cache_misses_total",
    "Total number of cache misses",
    ["cache_type"]
)

system_memory_bytes = Gauge(
    "postop_system_memory_bytes",
    "System memory usage in bytes",
    ["type"]  # used, available, percent
)

system_cpu_percent = Gauge(
    "postop_system_cpu_percent",
    "System CPU usage percentage"
)


class PrometheusExporter:
    """Prometheus metrics exporter."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize Prometheus exporter.
        
        Args:
            registry: Optional custom registry
        """
        self.registry = registry or REGISTRY
    
    def track_pdf_collected(
        self,
        source: str,
        procedure_type: str,
        quality: str
    ):
        """Track a collected PDF."""
        pdf_collected_total.labels(
            source=source,
            procedure_type=procedure_type,
            quality=quality
        ).inc()
    
    def track_collection_error(self, error_type: str, source: str):
        """Track a collection error."""
        pdf_collection_errors_total.labels(
            error_type=error_type,
            source=source
        ).inc()
    
    def track_api_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ):
        """Track an API request."""
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()
        
        api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def track_database_operation(
        self,
        operation: str,
        table: str,
        status: str,
        duration: float
    ):
        """Track a database operation."""
        database_operations_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()
        
        database_operation_duration_seconds.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def set_active_collections(self, count: int):
        """Set number of active collections."""
        active_collections.set(count)
    
    def set_storage_usage(self, bytes_used: int):
        """Set storage usage."""
        pdf_storage_bytes.set(bytes_used)
    
    def track_confidence_score(self, score: float, procedure_type: str):
        """Track PDF confidence score."""
        pdf_confidence_score.labels(
            procedure_type=procedure_type
        ).observe(score)
    
    def track_analysis_time(self, analysis_type: str, duration: float):
        """Track analysis processing time."""
        analysis_processing_time_seconds.labels(
            analysis_type=analysis_type
        ).observe(duration)
    
    def track_cache_hit(self, cache_type: str):
        """Track cache hit."""
        cache_hits_total.labels(cache_type=cache_type).inc()
    
    def track_cache_miss(self, cache_type: str):
        """Track cache miss."""
        cache_misses_total.labels(cache_type=cache_type).inc()
    
    def update_system_metrics(self):
        """Update system metrics."""
        try:
            import psutil
            
            # Memory metrics
            memory = psutil.virtual_memory()
            system_memory_bytes.labels(type="used").set(memory.used)
            system_memory_bytes.labels(type="available").set(memory.available)
            system_memory_bytes.labels(type="percent").set(memory.percent)
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_percent.set(cpu_percent)
            
        except ImportError:
            pass  # psutil not installed
    
    def generate_metrics(self) -> bytes:
        """Generate metrics in Prometheus format.
        
        Returns:
            Metrics data in Prometheus format
        """
        # Update system metrics before generating
        self.update_system_metrics()
        
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST


# Global exporter instance
_prometheus_exporter = PrometheusExporter()


def get_prometheus_metrics() -> bytes:
    """Get Prometheus metrics."""
    return _prometheus_exporter.generate_metrics()


def track_metric_prometheus(metric_name: str, value: Any, **labels):
    """Track a metric for Prometheus export.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        **labels: Label key-value pairs
    """
    # Map common metrics to Prometheus metrics
    if metric_name == "pdf.collected":
        _prometheus_exporter.track_pdf_collected(
            source=labels.get("source", "unknown"),
            procedure_type=labels.get("procedure_type", "unknown"),
            quality=labels.get("quality", "unknown")
        )
    elif metric_name == "api.request":
        _prometheus_exporter.track_api_request(
            method=labels.get("method", "GET"),
            endpoint=labels.get("endpoint", "/"),
            status=labels.get("status", 200),
            duration=value
        )
    elif metric_name == "database.operation":
        _prometheus_exporter.track_database_operation(
            operation=labels.get("operation", "select"),
            table=labels.get("table", "unknown"),
            status=labels.get("status", "success"),
            duration=value
        )
    # Add more metric mappings as needed