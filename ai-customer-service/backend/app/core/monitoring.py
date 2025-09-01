"""
Monitoring and Metrics Service

This module provides comprehensive monitoring, metrics collection,
and observability features for the AI Customer Service system.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import threading

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetric:
    """Performance metric with statistical aggregations."""
    name: str
    count: int = 0
    total: float = 0.0
    min_value: float = float('inf')
    max_value: float = float('-inf')
    avg_value: float = 0.0
    
    def add_value(self, value: float):
        """Add a new value to the metric."""
        self.count += 1
        self.total += value
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        self.avg_value = self.total / self.count


class MetricsCollector:
    """Centralized metrics collection and aggregation."""
    
    def __init__(self, max_points: int = 10000):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self._performance_metrics: Dict[str, PerformanceMetric] = {}
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def record_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Record a counter metric."""
        with self._lock:
            key = self._create_key(name, tags)
            self._counters[key] += value
            
            # Store as time series
            point = MetricPoint(name, value, datetime.utcnow(), tags or {})
            self._metrics[name].append(point)
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric."""
        with self._lock:
            key = self._create_key(name, tags)
            self._gauges[key] = value
            
            # Store as time series
            point = MetricPoint(name, value, datetime.utcnow(), tags or {})
            self._metrics[name].append(point)
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timer metric."""
        with self._lock:
            key = self._create_key(name, tags)
            
            if key not in self._performance_metrics:
                self._performance_metrics[key] = PerformanceMetric(name)
            
            self._performance_metrics[key].add_value(duration)
            
            # Store as time series
            point = MetricPoint(name, duration, datetime.utcnow(), tags or {})
            self._metrics[name].append(point)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "performance": {
                    key: {
                        "count": metric.count,
                        "avg": metric.avg_value,
                        "min": metric.min_value,
                        "max": metric.max_value,
                        "total": metric.total
                    }
                    for key, metric in self._performance_metrics.items()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_time_series(self, metric_name: str, since: datetime = None) -> List[Dict[str, Any]]:
        """Get time series data for a specific metric."""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=1)
        
        with self._lock:
            points = self._metrics.get(metric_name, deque())
            return [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "value": point.value,
                    "tags": point.tags
                }
                for point in points
                if point.timestamp >= since
            ]
    
    def _create_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Create a unique key for the metric."""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


class HealthChecker:
    """Health check manager for system components."""
    
    def __init__(self):
        self._checks: Dict[str, callable] = {}
        self._last_results: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def register_check(self, name: str, check_func: callable, timeout: int = 30):
        """Register a health check function."""
        self._checks[name] = {
            "func": check_func,
            "timeout": timeout
        }
        logger.info(f"Registered health check: {name}")
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks and return results."""
        results = {}
        overall_status = "healthy"
        
        for name, check_config in self._checks.items():
            try:
                start_time = time.time()
                
                # Run check with timeout
                if asyncio.iscoroutinefunction(check_config["func"]):
                    result = await asyncio.wait_for(
                        check_config["func"](),
                        timeout=check_config["timeout"]
                    )
                else:
                    result = check_config["func"]()
                
                duration = time.time() - start_time
                
                results[name] = {
                    "status": "healthy",
                    "duration": duration,
                    "details": result if isinstance(result, dict) else {"result": result},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except asyncio.TimeoutError:
                results[name] = {
                    "status": "timeout",
                    "duration": check_config["timeout"],
                    "error": "Health check timed out",
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_status = "degraded"
                
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_status = "unhealthy"
        
        with self._lock:
            self._last_results = results
        
        return {
            "status": overall_status,
            "checks": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_last_results(self) -> Dict[str, Any]:
        """Get the last health check results."""
        with self._lock:
            return self._last_results.copy()


class PerformanceMonitor:
    """Performance monitoring and alerting."""
    
    def __init__(self):
        self._thresholds: Dict[str, Dict[str, float]] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def set_threshold(self, metric_name: str, warning: float = None, critical: float = None):
        """Set performance thresholds for a metric."""
        self._thresholds[metric_name] = {
            "warning": warning,
            "critical": critical
        }
    
    def check_thresholds(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds and generate alerts."""
        alerts = []
        
        for metric_name, thresholds in self._thresholds.items():
            if metric_name in metrics:
                value = metrics[metric_name]
                
                if thresholds["critical"] and value >= thresholds["critical"]:
                    alerts.append({
                        "level": "critical",
                        "metric": metric_name,
                        "value": value,
                        "threshold": thresholds["critical"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif thresholds["warning"] and value >= thresholds["warning"]:
                    alerts.append({
                        "level": "warning",
                        "metric": metric_name,
                        "value": value,
                        "threshold": thresholds["warning"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        with self._lock:
            self._alerts.extend(alerts)
            # Keep only recent alerts (last 1000)
            self._alerts = self._alerts[-1000:]
        
        return alerts
    
    def get_alerts(self, level: str = None) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered by level."""
        with self._lock:
            if level:
                return [alert for alert in self._alerts if alert["level"] == level]
            return self._alerts.copy()


# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker()
performance_monitor = PerformanceMonitor()


def timer_decorator(metric_name: str, tags: Dict[str, str] = None):
    """Decorator to automatically time function execution."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                metrics_collector.record_timer(
                    f"{metric_name}.success",
                    time.time() - start_time,
                    tags
                )
                return result
            except Exception as e:
                metrics_collector.record_timer(
                    f"{metric_name}.error",
                    time.time() - start_time,
                    {**(tags or {}), "error_type": type(e).__name__}
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metrics_collector.record_timer(
                    f"{metric_name}.success",
                    time.time() - start_time,
                    tags
                )
                return result
            except Exception as e:
                metrics_collector.record_timer(
                    f"{metric_name}.error",
                    time.time() - start_time,
                    {**(tags or {}), "error_type": type(e).__name__}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Health check functions
async def database_health_check():
    """Check database connectivity."""
    from app.core.database import SessionLocal
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "connected"}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


async def redis_health_check():
    """Check Redis connectivity."""
    try:
        from app.application.services import CacheService
        cache = CacheService()
        await cache.set("health_check", "ok", 5)
        result = await cache.get("health_check")
        await cache.delete("health_check")
        return {"status": "connected", "test_result": result}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


async def ai_service_health_check():
    """Check AI service connectivity."""
    try:
        from app.services.ai_service import ai_service
        # Simple test to ensure AI service is responsive
        response = await ai_service.generate_response(
            message="Health check",
            conversation_history=[],
            context_type="health_check"
        )
        return {"status": "connected", "model": response.get("model", "unknown")}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


# Register health checks
health_checker.register_check("database", database_health_check)
health_checker.register_check("redis", redis_health_check)
health_checker.register_check("ai_service", ai_service_health_check)

# Set performance thresholds
performance_monitor.set_threshold("response_time", warning=1.0, critical=5.0)
performance_monitor.set_threshold("error_rate", warning=0.05, critical=0.1)
performance_monitor.set_threshold("memory_usage", warning=0.8, critical=0.95)
