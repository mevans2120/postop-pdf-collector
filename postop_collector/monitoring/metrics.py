"""Metrics collection and monitoring."""

import time
import json
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import statistics


class MetricsCollector:
    """Collects and aggregates application metrics."""
    
    def __init__(self, flush_interval: int = 60):
        """Initialize metrics collector.
        
        Args:
            flush_interval: Interval in seconds to flush metrics to storage
        """
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.timers = {}
        self.flush_interval = flush_interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._flush_thread = None
        
        # Keep rolling window of metrics (last hour)
        self.window_size = 3600  # 1 hour in seconds
        self.time_series = defaultdict(lambda: deque(maxlen=self.window_size))
    
    def start(self):
        """Start the metrics collector."""
        if not self._flush_thread:
            self._flush_thread = threading.Thread(target=self._flush_loop)
            self._flush_thread.daemon = True
            self._flush_thread.start()
    
    def stop(self):
        """Stop the metrics collector."""
        self._stop_event.set()
        if self._flush_thread:
            self._flush_thread.join()
    
    def _flush_loop(self):
        """Background thread to periodically flush metrics."""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.flush_interval)
            if not self._stop_event.is_set():
                self.flush()
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict] = None):
        """Increment a counter metric.
        
        Args:
            name: Metric name
            value: Value to increment by
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._make_key(name, tags)
            self.counters[key] += value
            self.time_series[key].append((time.time(), value))
    
    def gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """Set a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value
            self.time_series[key].append((time.time(), value))
    
    def histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """Add a value to a histogram metric.
        
        Args:
            name: Metric name
            value: Value to add to histogram
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._make_key(name, tags)
            self.histograms[key].append(value)
            self.time_series[key].append((time.time(), value))
    
    def timer_start(self, name: str, tags: Optional[Dict] = None):
        """Start a timer.
        
        Args:
            name: Timer name
            tags: Optional tags for the timer
        """
        key = self._make_key(name, tags)
        self.timers[key] = time.time()
    
    def timer_end(self, name: str, tags: Optional[Dict] = None):
        """End a timer and record duration.
        
        Args:
            name: Timer name
            tags: Optional tags for the timer
        """
        key = self._make_key(name, tags)
        if key in self.timers:
            duration = time.time() - self.timers[key]
            self.histogram(f"{name}.duration", duration * 1000, tags)  # ms
            del self.timers[key]
    
    def _make_key(self, name: str, tags: Optional[Dict] = None) -> str:
        """Create a metric key from name and tags."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name},{tag_str}"
    
    def get_stats(self, name: str, tags: Optional[Dict] = None) -> Dict[str, Any]:
        """Get statistics for a metric.
        
        Args:
            name: Metric name
            tags: Optional tags
            
        Returns:
            Dictionary with metric statistics
        """
        key = self._make_key(name, tags)
        
        with self._lock:
            stats = {}
            
            # Counter stats
            if key in self.counters:
                stats["count"] = self.counters[key]
            
            # Gauge stats
            if key in self.gauges:
                stats["value"] = self.gauges[key]
            
            # Histogram stats
            if key in self.histograms:
                values = self.histograms[key]
                if values:
                    stats["histogram"] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99),
                    }
            
            # Time series stats
            if key in self.time_series:
                recent_values = [v for _, v in self.time_series[key]]
                if recent_values:
                    stats["recent"] = {
                        "last": recent_values[-1],
                        "avg_1m": self._recent_average(key, 60),
                        "avg_5m": self._recent_average(key, 300),
                        "avg_1h": self._recent_average(key, 3600),
                    }
            
            return stats
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _recent_average(self, key: str, seconds: int) -> float:
        """Calculate average of recent values."""
        cutoff = time.time() - seconds
        recent = [v for t, v in self.time_series[key] if t > cutoff]
        return statistics.mean(recent) if recent else 0.0
    
    def flush(self, filepath: Optional[str] = None):
        """Flush metrics to file or stdout.
        
        Args:
            filepath: Optional file path to write metrics to
        """
        with self._lock:
            metrics_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    k: self.get_stats(k.split(",")[0], self._parse_tags(k))
                    for k in self.histograms
                },
            }
        
        if filepath:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "a") as f:
                f.write(json.dumps(metrics_data) + "\n")
        else:
            print(json.dumps(metrics_data, indent=2))
    
    def _parse_tags(self, key: str) -> Optional[Dict]:
        """Parse tags from metric key."""
        parts = key.split(",")
        if len(parts) <= 1:
            return None
        tags = {}
        for part in parts[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                tags[k] = v
        return tags if tags else None
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics.
        
        Returns:
            Dictionary containing all metrics
        """
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    k: self.get_stats(k.split(",")[0], self._parse_tags(k))
                    for k in self.histograms
                },
                "active_timers": list(self.timers.keys()),
            }


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def track_metric(metric_type: str, name: str, value: Any = 1, tags: Optional[Dict] = None):
    """Track a metric using the global collector.
    
    Args:
        metric_type: Type of metric (counter, gauge, histogram)
        name: Metric name
        value: Metric value
        tags: Optional tags
    """
    if metric_type == "counter":
        _metrics_collector.increment(name, value, tags)
    elif metric_type == "gauge":
        _metrics_collector.gauge(name, value, tags)
    elif metric_type == "histogram":
        _metrics_collector.histogram(name, value, tags)


def get_metrics() -> Dict[str, Any]:
    """Get all metrics from the global collector."""
    return _metrics_collector.get_all_metrics()


class MetricsContext:
    """Context manager for tracking metrics within a scope."""
    
    def __init__(self, name: str, tags: Optional[Dict] = None):
        """Initialize metrics context.
        
        Args:
            name: Base name for metrics
            tags: Optional tags
        """
        self.name = name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        """Enter context and start timer."""
        self.start_time = time.time()
        _metrics_collector.increment(f"{self.name}.started", tags=self.tags)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and record metrics."""
        duration = (time.time() - self.start_time) * 1000  # ms
        
        if exc_type is None:
            _metrics_collector.increment(f"{self.name}.success", tags=self.tags)
        else:
            _metrics_collector.increment(f"{self.name}.error", tags=self.tags)
            error_tags = {**self.tags, "error": exc_type.__name__}
            _metrics_collector.increment(f"{self.name}.error_type", tags=error_tags)
        
        _metrics_collector.histogram(f"{self.name}.duration_ms", duration, tags=self.tags)