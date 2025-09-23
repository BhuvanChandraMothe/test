# monitoring/metrics.py - Metrics and Monitoring Documentation

## Overview
The `monitoring/metrics.py` file implements comprehensive monitoring and metrics collection for the SAP OData Connector. It provides real-time performance tracking, alerting, and observability features for production deployments.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict, deque
import structlog
import threading
from enum import Enum

from config.models import ODataConfig
```

**Library Concepts:**
- **collections.defaultdict**: Automatic dictionary initialization
- **collections.deque**: Efficient queue for time-series data
- **threading**: Thread-safe operations for concurrent access
- **enum**: Type-safe enumeration for metric types
- **dataclasses**: Structured metric data containers

### MetricType Enumeration
```python
class MetricType(Enum):
    """Types of metrics collected"""
    COUNTER = "counter"        # Monotonically increasing values
    GAUGE = "gauge"           # Current state values
    HISTOGRAM = "histogram"   # Distribution of values
    TIMER = "timer"          # Duration measurements
    RATE = "rate"            # Events per time unit
```

**Metric Type Concepts:**
- **Counter**: Total requests, errors, records processed
- **Gauge**: Active connections, queue size, memory usage
- **Histogram**: Response times, batch sizes, record counts
- **Timer**: Operation durations, request latencies
- **Rate**: Requests per second, throughput metrics

### Metric Data Classes
```python
@dataclass
class MetricPoint:
    """Single metric measurement"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE

@dataclass
class TimeSeries:
    """Time series data for a metric"""
    name: str
    metric_type: MetricType
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def add_point(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """Add a new data point"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        point = MetricPoint(
            name=self.name,
            value=value,
            timestamp=timestamp,
            tags=self.tags,
            metric_type=self.metric_type
        )
        self.points.append(point)
    
    def get_latest(self) -> Optional[MetricPoint]:
        """Get the most recent data point"""
        return self.points[-1] if self.points else None
    
    def get_average(self, window_seconds: int = 300) -> float:
        """Get average value over time window"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - window_seconds
        
        values = [
            point.value for point in self.points
            if point.timestamp.timestamp() > cutoff_time
        ]
        
        return sum(values) / len(values) if values else 0.0
```

**Time Series Design:**
- **Bounded storage**: Use deque with maxlen to limit memory usage
- **Timestamp tracking**: All metrics include precise timestamps
- **Tag support**: Dimensional metrics with key-value tags
- **Window calculations**: Compute statistics over time periods
- **Latest value access**: Quick access to current state

### MetricsCollector Class
```python
class MetricsCollector:
    """Collects and manages application metrics"""
    
    def __init__(self, max_series_points: int = 1000):
        self.max_series_points = max_series_points
        self.metrics: Dict[str, TimeSeries] = {}
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Built-in metrics
        self._initialize_builtin_metrics()
        
        self.logger = structlog.get_logger(__name__)
    
    def _initialize_builtin_metrics(self) -> None:
        """Initialize standard connector metrics"""
        builtin_metrics = [
            ("odata.requests.total", MetricType.COUNTER),
            ("odata.requests.success", MetricType.COUNTER),
            ("odata.requests.error", MetricType.COUNTER),
            ("odata.records.fetched", MetricType.COUNTER),
            ("odata.bytes.downloaded", MetricType.COUNTER),
            ("odata.active_connections", MetricType.GAUGE),
            ("odata.queue_size", MetricType.GAUGE),
            ("odata.response_time", MetricType.HISTOGRAM),
            ("odata.batch_size", MetricType.HISTOGRAM),
            ("odata.throughput", MetricType.RATE)
        ]
        
        for name, metric_type in builtin_metrics:
            self.create_metric(name, metric_type)
```

**Metrics Collection Features:**
- **Thread safety**: Use RLock for concurrent access
- **Multiple metric types**: Support counters, gauges, histograms
- **Built-in metrics**: Standard OData connector metrics
- **Memory management**: Bounded time series storage
- **Initialization**: Set up common metrics automatically

### Metric Recording Methods
```python
def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
    """Increment a counter metric"""
    with self._lock:
        full_name = self._build_metric_name(name, tags)
        self.counters[full_name] += value
        
        # Also record in time series
        if name in self.metrics:
            self.metrics[name].add_point(self.counters[full_name])
        
        self.logger.debug("Counter incremented", 
                         metric=name, 
                         value=value, 
                         total=self.counters[full_name])

def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """Set a gauge metric value"""
    with self._lock:
        full_name = self._build_metric_name(name, tags)
        self.gauges[full_name] = value
        
        # Record in time series
        if name in self.metrics:
            self.metrics[name].add_point(value)
        
        self.logger.debug("Gauge set", metric=name, value=value)

def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """Record a histogram value"""
    with self._lock:
        if name in self.metrics:
            self.metrics[name].add_point(value)
        
        self.logger.debug("Histogram recorded", metric=name, value=value)

def time_operation(self, name: str, tags: Optional[Dict[str, str]] = None):
    """Context manager for timing operations"""
    return TimerContext(self, name, tags)

def _build_metric_name(self, name: str, tags: Optional[Dict[str, str]]) -> str:
    """Build metric name with tags"""
    if not tags:
        return name
    
    tag_string = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    return f"{name}[{tag_string}]"
```

**Recording Methods:**
- **Counter increment**: Monotonically increasing values
- **Gauge setting**: Current state values
- **Histogram recording**: Distribution tracking
- **Timer context**: Automatic duration measurement
- **Tag support**: Dimensional metrics with labels

### Timer Context Manager
```python
class TimerContext:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            self.collector.record_histogram(self.name, duration, self.tags)
            
            # Also record success/failure
            if exc_type is None:
                self.collector.increment_counter(f"{self.name}.success", tags=self.tags)
            else:
                self.collector.increment_counter(f"{self.name}.error", tags=self.tags)

# Usage example:
# with metrics.time_operation("odata.request", {"entity": "Products"}):
#     response = await make_request()
```

**Timer Features:**
- **High precision**: Use perf_counter for accurate timing
- **Automatic recording**: Record duration on context exit
- **Success/failure tracking**: Separate counters for outcomes
- **Exception handling**: Record metrics even if operation fails

### Performance Monitor
```python
class PerformanceMonitor:
    """Monitors system and application performance"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.logger = structlog.get_logger(__name__)
    
    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        
        self.logger.info("Performance monitoring started", interval=interval_seconds)
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self.monitoring_active = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self._collect_system_metrics()
                await self._collect_application_metrics()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Monitoring error", error=str(e))
                await asyncio.sleep(interval_seconds)
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.set_gauge("system.cpu.usage", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics.set_gauge("system.memory.usage", memory.percent)
            self.metrics.set_gauge("system.memory.available", memory.available)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.metrics.set_gauge("system.disk.usage", disk.percent)
            
        except ImportError:
            # psutil not available
            pass
        except Exception as e:
            self.logger.warning("System metrics collection failed", error=str(e))
    
    async def _collect_application_metrics(self) -> None:
        """Collect application-specific metrics"""
        try:
            # Calculate rates from counters
            self._calculate_rates()
            
            # Record current timestamp for rate calculations
            self.metrics.set_gauge("app.last_metric_collection", time.time())
            
        except Exception as e:
            self.logger.error("Application metrics collection failed", error=str(e))
    
    def _calculate_rates(self) -> None:
        """Calculate rate metrics from counters"""
        # This is a simplified implementation
        # In production, you'd track previous values and time windows
        
        current_time = time.time()
        
        # Example: requests per second
        total_requests = self.metrics.counters.get("odata.requests.total", 0)
        if hasattr(self, '_last_request_count') and hasattr(self, '_last_request_time'):
            time_diff = current_time - self._last_request_time
            request_diff = total_requests - self._last_request_count
            
            if time_diff > 0:
                rps = request_diff / time_diff
                self.metrics.set_gauge("odata.requests.rate", rps)
        
        self._last_request_count = total_requests
        self._last_request_time = current_time
```

**Performance Monitoring Features:**
- **System metrics**: CPU, memory, disk usage via psutil
- **Application metrics**: Custom business metrics
- **Rate calculations**: Derive rates from counters
- **Async monitoring**: Non-blocking background collection
- **Error resilience**: Continue monitoring despite failures

### Alert Manager
```python
@dataclass
class AlertRule:
    """Definition of an alert condition"""
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne"
    threshold: float
    duration_seconds: int = 300  # How long condition must persist
    severity: str = "warning"    # "info", "warning", "error", "critical"
    message_template: str = "Alert: {metric} {condition} {threshold}"

class AlertManager:
    """Manages alerts based on metric thresholds"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, datetime] = {}
        self.alert_callbacks: List[Callable[[str, AlertRule], None]] = []
        self.logger = structlog.get_logger(__name__)
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule"""
        self.alert_rules.append(rule)
        self.logger.info("Alert rule added", rule=rule.name)
    
    def add_alert_callback(self, callback: Callable[[str, AlertRule], None]) -> None:
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    async def check_alerts(self) -> List[str]:
        """Check all alert rules and trigger alerts"""
        triggered_alerts = []
        
        for rule in self.alert_rules:
            if await self._evaluate_rule(rule):
                alert_key = f"{rule.name}:{rule.metric_name}"
                
                # Check if this is a new alert or existing
                if alert_key not in self.active_alerts:
                    self.active_alerts[alert_key] = datetime.now(timezone.utc)
                    triggered_alerts.append(alert_key)
                    
                    # Trigger callbacks
                    message = rule.message_template.format(
                        metric=rule.metric_name,
                        condition=rule.condition,
                        threshold=rule.threshold
                    )
                    
                    for callback in self.alert_callbacks:
                        try:
                            callback(message, rule)
                        except Exception as e:
                            self.logger.error("Alert callback failed", error=str(e))
                    
                    self.logger.warning("Alert triggered", 
                                      rule=rule.name,
                                      metric=rule.metric_name,
                                      severity=rule.severity)
            else:
                # Clear alert if condition no longer met
                alert_key = f"{rule.name}:{rule.metric_name}"
                if alert_key in self.active_alerts:
                    del self.active_alerts[alert_key]
                    self.logger.info("Alert cleared", rule=rule.name)
        
        return triggered_alerts
    
    async def _evaluate_rule(self, rule: AlertRule) -> bool:
        """Evaluate if an alert rule condition is met"""
        if rule.metric_name not in self.metrics.metrics:
            return False
        
        metric = self.metrics.metrics[rule.metric_name]
        latest_point = metric.get_latest()
        
        if not latest_point:
            return False
        
        # Check if condition has persisted for required duration
        alert_key = f"{rule.name}:{rule.metric_name}"
        if alert_key in self.active_alerts:
            alert_start = self.active_alerts[alert_key]
            duration = (datetime.now(timezone.utc) - alert_start).total_seconds()
            if duration < rule.duration_seconds:
                return False
        
        # Evaluate condition
        value = latest_point.value
        
        if rule.condition == "gt":
            return value > rule.threshold
        elif rule.condition == "lt":
            return value < rule.threshold
        elif rule.condition == "eq":
            return value == rule.threshold
        elif rule.condition == "ne":
            return value != rule.threshold
        
        return False
```

**Alert Management Features:**
- **Rule-based alerts**: Define conditions and thresholds
- **Duration requirements**: Prevent flapping alerts
- **Severity levels**: Categorize alert importance
- **Callback system**: Pluggable notification mechanisms
- **Alert lifecycle**: Track active alerts and clearance

### Metrics Export and Reporting
```python
class MetricsExporter:
    """Exports metrics to external systems"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.logger = structlog.get_logger(__name__)
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Export counters
        for name, value in self.metrics.counters.items():
            clean_name = self._clean_prometheus_name(name)
            lines.append(f"# TYPE {clean_name} counter")
            lines.append(f"{clean_name} {value}")
        
        # Export gauges
        for name, value in self.metrics.gauges.items():
            clean_name = self._clean_prometheus_name(name)
            lines.append(f"# TYPE {clean_name} gauge")
            lines.append(f"{clean_name} {value}")
        
        return "\n".join(lines)
    
    def export_json(self) -> Dict[str, Any]:
        """Export metrics as JSON"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counters": dict(self.metrics.counters),
            "gauges": dict(self.metrics.gauges),
            "time_series": {
                name: {
                    "type": series.metric_type.value,
                    "latest_value": series.get_latest().value if series.get_latest() else None,
                    "point_count": len(series.points)
                }
                for name, series in self.metrics.metrics.items()
            }
        }
    
    def _clean_prometheus_name(self, name: str) -> str:
        """Clean metric name for Prometheus format"""
        # Replace invalid characters with underscores
        import re
        return re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    async def export_to_file(self, file_path: str, format: str = "json") -> None:
        """Export metrics to file"""
        try:
            if format == "json":
                data = self.export_json()
                content = json.dumps(data, indent=2)
            elif format == "prometheus":
                content = self.export_prometheus()
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            self.logger.info("Metrics exported", file_path=file_path, format=format)
            
        except Exception as e:
            self.logger.error("Metrics export failed", error=str(e))
```

**Export Features:**
- **Multiple formats**: JSON, Prometheus, custom formats
- **File export**: Save metrics to disk
- **Name cleaning**: Format-specific name sanitization
- **Structured output**: Well-formatted metric data
- **Error handling**: Graceful failure handling

## Advanced Monitoring Concepts

### Custom Metric Types
```python
class DistributionMetric:
    """Track distribution of values with percentiles"""
    
    def __init__(self, name: str, max_values: int = 1000):
        self.name = name
        self.values = deque(maxlen=max_values)
        self._lock = threading.Lock()
    
    def record(self, value: float) -> None:
        with self._lock:
            self.values.append(value)
    
    def get_percentile(self, percentile: float) -> float:
        """Get percentile value (0.0 to 1.0)"""
        with self._lock:
            if not self.values:
                return 0.0
            
            sorted_values = sorted(self.values)
            index = int(percentile * (len(sorted_values) - 1))
            return sorted_values[index]
    
    def get_statistics(self) -> Dict[str, float]:
        """Get comprehensive statistics"""
        with self._lock:
            if not self.values:
                return {}
            
            sorted_values = sorted(self.values)
            return {
                "count": len(sorted_values),
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "mean": sum(sorted_values) / len(sorted_values),
                "p50": self.get_percentile(0.5),
                "p95": self.get_percentile(0.95),
                "p99": self.get_percentile(0.99)
            }
```

### Health Check Integration
```python
class HealthCheckMonitor:
    """Monitor application health status"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.health_checks: Dict[str, Callable[[], bool]] = {}
        self.logger = structlog.get_logger(__name__)
    
    def register_health_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register a health check function"""
        self.health_checks[name] = check_func
    
    async def run_health_checks(self) -> Dict[str, bool]:
        """Run all health checks"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                is_healthy = check_func()
                results[name] = is_healthy
                
                # Record as metric
                self.metrics.set_gauge(f"health.{name}", 1.0 if is_healthy else 0.0)
                
            except Exception as e:
                self.logger.error("Health check failed", check=name, error=str(e))
                results[name] = False
                self.metrics.set_gauge(f"health.{name}", 0.0)
        
        # Overall health
        overall_healthy = all(results.values())
        self.metrics.set_gauge("health.overall", 1.0 if overall_healthy else 0.0)
        
        return results
```

## Key Programming Concepts

### 1. **Thread-Safe Metrics Collection**
```python
import threading

class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, amount=1):
        with self._lock:
            self._value += amount
    
    @property
    def value(self):
        with self._lock:
            return self._value
```

### 2. **Time-Based Metric Windows**
```python
def get_metrics_in_window(metrics: deque, window_seconds: int) -> List:
    cutoff_time = time.time() - window_seconds
    return [m for m in metrics if m.timestamp > cutoff_time]
```

### 3. **Context Manager for Timing**
```python
import time
from contextlib import contextmanager

@contextmanager
def timer(metric_name: str, collector):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        collector.record_histogram(metric_name, duration)
```

### 4. **Metric Aggregation**
```python
def aggregate_metrics(metrics: List[float], aggregation: str) -> float:
    if not metrics:
        return 0.0
    
    if aggregation == "sum":
        return sum(metrics)
    elif aggregation == "avg":
        return sum(metrics) / len(metrics)
    elif aggregation == "max":
        return max(metrics)
    elif aggregation == "min":
        return min(metrics)
    else:
        return 0.0
```

## Usage Examples

### Basic Metrics Collection
```python
from monitoring.metrics import MetricsCollector, PerformanceMonitor

metrics = MetricsCollector()

# Record metrics
metrics.increment_counter("requests.total")
metrics.set_gauge("active_connections", 5)
metrics.record_histogram("response_time", 0.150)

# Time operations
with metrics.time_operation("database.query"):
    result = await database.query("SELECT * FROM products")
```

### Alert Configuration
```python
from monitoring.metrics import AlertManager, AlertRule

alert_manager = AlertManager(metrics)

# Add alert rules
high_error_rate = AlertRule(
    name="high_error_rate",
    metric_name="requests.error_rate",
    condition="gt",
    threshold=0.05,  # 5% error rate
    duration_seconds=300,
    severity="warning"
)

alert_manager.add_alert_rule(high_error_rate)

# Add notification callback
def send_alert(message: str, rule: AlertRule):
    print(f"ALERT [{rule.severity}]: {message}")

alert_manager.add_alert_callback(send_alert)

# Check alerts periodically
triggered = await alert_manager.check_alerts()
```

### Performance Monitoring
```python
monitor = PerformanceMonitor(metrics)

# Start background monitoring
await monitor.start_monitoring(interval_seconds=30)

# Your application runs here...

# Stop monitoring
await monitor.stop_monitoring()
```

### Metrics Export
```python
from monitoring.metrics import MetricsExporter

exporter = MetricsExporter(metrics)

# Export to Prometheus format
prometheus_data = exporter.export_prometheus()

# Export to JSON file
await exporter.export_to_file("metrics.json", format="json")
```

This file demonstrates enterprise-grade monitoring and observability with comprehensive metrics collection, alerting, and export capabilities for production SAP OData connector deployments.
