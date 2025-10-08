# """Metrics and monitoring for SAP OData connector"""

# import asyncio
# import time
# from typing import Dict, List, Any, Optional
# from dataclasses import dataclass, field
# from enum import Enum
# import structlog
# from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
# from datetime import datetime, timezone

# logger = structlog.get_logger(__name__)


# class MetricType(Enum):
#     """Types of metrics"""
#     COUNTER = "counter"
#     HISTOGRAM = "histogram"
#     GAUGE = "gauge"


# @dataclass
# class ConnectorMetrics:
#     """Container for all connector metrics"""
    
#     # Request metrics
#     requests_total: Counter = field(default_factory=lambda: Counter(
#         'sap_odata_requests_total',
#         'Total number of OData requests',
#         ['entity', 'status', 'worker_id']
#     ))
    
#     request_duration: Histogram = field(default_factory=lambda: Histogram(
#         'sap_odata_request_duration_seconds',
#         'Request duration in seconds',
#         ['entity', 'worker_id']
#     ))
    
#     # Processing metrics
#     records_processed: Counter = field(default_factory=lambda: Counter(
#         'sap_odata_records_processed_total',
#         'Total number of records processed',
#         ['entity', 'status']
#     ))
    
#     transformation_duration: Histogram = field(default_factory=lambda: Histogram(
#         'sap_odata_transformation_duration_seconds',
#         'Transformation duration in seconds',
#         ['entity']
#     ))
    
#     # Queue metrics
#     queue_size: Gauge = field(default_factory=lambda: Gauge(
#         'sap_odata_queue_size',
#         'Current queue size'
#     ))
    
#     active_workers: Gauge = field(default_factory=lambda: Gauge(
#         'sap_odata_active_workers',
#         'Number of active workers'
#     ))
    
#     # Error metrics
#     errors_total: Counter = field(default_factory=lambda: Counter(
#         'sap_odata_errors_total',
#         'Total number of errors',
#         ['entity', 'error_type', 'worker_id']
#     ))
    
#     circuit_breaker_state: Gauge = field(default_factory=lambda: Gauge(
#         'sap_odata_circuit_breaker_state',
#         'Circuit breaker state (0=closed, 1=open, 2=half_open)',
#         ['worker_id']
#     ))
    
#     # Storage metrics
#     storage_operations: Counter = field(default_factory=lambda: Counter(
#         'sap_odata_storage_operations_total',
#         'Total storage operations',
#         ['storage_type', 'operation', 'status']
#     ))
    
#     storage_duration: Histogram = field(default_factory=lambda: Histogram(
#         'sap_odata_storage_duration_seconds',
#         'Storage operation duration',
#         ['storage_type', 'operation']
#     ))


# class MetricsCollector:
#     """Collects and manages metrics for the SAP OData connector"""
    
#     def __init__(self, registry: Optional[CollectorRegistry] = None):
#         self.registry = registry or CollectorRegistry()
#         self.metrics = ConnectorMetrics()
#         self._start_time = time.time()
#         self._custom_metrics: Dict[str, Any] = {}
        
#         # Register all metrics
#         self._register_metrics()
    
#     def _register_metrics(self):
#         """Register all metrics with the registry"""
#         for metric_name, metric in self.metrics.__dict__.items():
#             if hasattr(metric, '_name'):
#                 self.registry.register(metric)
    
#     def record_request(
#         self,
#         entity: str,
#         worker_id: str,
#         duration: float,
#         success: bool,
#         error_type: Optional[str] = None
#     ):
#         """Record a request metric"""
#         status = "success" if success else "error"
        
#         self.metrics.requests_total.labels(
#             entity=entity,
#             status=status,
#             worker_id=worker_id
#         ).inc()
        
#         self.metrics.request_duration.labels(
#             entity=entity,
#             worker_id=worker_id
#         ).observe(duration)
        
#         if not success and error_type:
#             self.metrics.errors_total.labels(
#                 entity=entity,
#                 error_type=error_type,
#                 worker_id=worker_id
#             ).inc()
    
#     def record_records_processed(
#         self,
#         entity: str,
#         count: int,
#         success: bool
#     ):
#         """Record processed records metric"""
#         status = "success" if success else "error"
        
#         self.metrics.records_processed.labels(
#             entity=entity,
#             status=status
#         ).inc(count)
    
#     def record_transformation(
#         self,
#         entity: str,
#         duration: float
#     ):
#         """Record transformation metric"""
#         self.metrics.transformation_duration.labels(
#             entity=entity
#         ).observe(duration)
    
#     def update_queue_size(self, size: int):
#         """Update queue size metric"""
#         self.metrics.queue_size.set(size)
    
#     def update_active_workers(self, count: int):
#         """Update active workers metric"""
#         self.metrics.active_workers.set(count)
    
#     def update_circuit_breaker_state(
#         self,
#         worker_id: str,
#         state: str
#     ):
#         """Update circuit breaker state metric"""
#         state_mapping = {
#             'closed': 0,
#             'open': 1,
#             'half_open': 2
#         }
        
#         self.metrics.circuit_breaker_state.labels(
#             worker_id=worker_id
#         ).set(state_mapping.get(state, 0))
    
#     def record_storage_operation(
#         self,
#         storage_type: str,
#         operation: str,
#         duration: float,
#         success: bool
#     ):
#         """Record storage operation metric"""
#         status = "success" if success else "error"
        
#         self.metrics.storage_operations.labels(
#             storage_type=storage_type,
#             operation=operation,
#             status=status
#         ).inc()
        
#         self.metrics.storage_duration.labels(
#             storage_type=storage_type,
#             operation=operation
#         ).observe(duration)
    
#     def get_metrics_text(self) -> str:
#         """Get metrics in Prometheus text format"""
#         return generate_latest(self.registry).decode('utf-8')
    
#     def get_summary_stats(self) -> Dict[str, Any]:
#         """Get summary statistics"""
#         uptime = time.time() - self._start_time
        
#         return {
#             'uptime_seconds': uptime,
#             'uptime_formatted': self._format_duration(uptime),
#             'start_time': datetime.fromtimestamp(self._start_time, tz=timezone.utc).isoformat(),
#             'current_time': datetime.now(timezone.utc).isoformat()
#         }
    
#     def _format_duration(self, seconds: float) -> str:
#         """Format duration in human-readable format"""
#         hours, remainder = divmod(int(seconds), 3600)
#         minutes, seconds = divmod(remainder, 60)
#         return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# class PerformanceMonitor:
#     """Monitors performance and health of the connector"""
    
#     def __init__(self, metrics_collector: MetricsCollector):
#         self.metrics = metrics_collector
#         self._health_checks: Dict[str, callable] = {}
#         self._alerts: List[Dict[str, Any]] = []
#         self._thresholds = {
#             'error_rate_threshold': 0.1,  # 10%
#             'avg_response_time_threshold': 30.0,  # 30 seconds
#             'queue_size_threshold': 1000
#         }
    
#     def add_health_check(self, name: str, check_func: callable):
#         """Add a health check function"""
#         self._health_checks[name] = check_func
    
#     async def run_health_checks(self) -> Dict[str, Any]:
#         """Run all health checks"""
#         results = {}
#         overall_healthy = True
        
#         for name, check_func in self._health_checks.items():
#             try:
#                 result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
#                 results[name] = {
#                     'status': 'healthy' if result else 'unhealthy',
#                     'result': result
#                 }
#                 if not result:
#                     overall_healthy = False
#             except Exception as e:
#                 results[name] = {
#                     'status': 'error',
#                     'error': str(e)
#                 }
#                 overall_healthy = False
        
#         results['overall'] = 'healthy' if overall_healthy else 'unhealthy'
#         return results
    
#     def check_performance_thresholds(self) -> List[Dict[str, Any]]:
#         """Check if performance metrics exceed thresholds"""
#         alerts = []
        
#         # This would typically query the actual metric values
#         # For now, we'll return the structure
        
#         return alerts
    
#     def get_performance_summary(self) -> Dict[str, Any]:
#         """Get performance summary"""
#         return {
#             'thresholds': self._thresholds,
#             'recent_alerts': self._alerts[-10:],  # Last 10 alerts
#             'health_status': 'monitoring'
#         }


# class AlertManager:
#     """Manages alerts and notifications"""
    
#     def __init__(self, metrics_collector: MetricsCollector):
#         self.metrics = metrics_collector
#         self._alert_handlers: List[callable] = []
#         self._alert_history: List[Dict[str, Any]] = []
    
#     def add_alert_handler(self, handler: callable):
#         """Add an alert handler function"""
#         self._alert_handlers.append(handler)
    
#     async def trigger_alert(
#         self,
#         severity: str,
#         title: str,
#         message: str,
#         metadata: Optional[Dict[str, Any]] = None
#     ):
#         """Trigger an alert"""
#         alert = {
#             'timestamp': datetime.now(timezone.utc).isoformat(),
#             'severity': severity,
#             'title': title,
#             'message': message,
#             'metadata': metadata or {}
#         }
        
#         self._alert_history.append(alert)
        
#         # Keep only last 1000 alerts
#         if len(self._alert_history) > 1000:
#             self._alert_history = self._alert_history[-1000:]
        
#         logger.warning("Alert triggered",
#                       severity=severity,
#                       title=title,
#                       message=message)
        
#         # Call alert handlers
#         for handler in self._alert_handlers:
#             try:
#                 if asyncio.iscoroutinefunction(handler):
#                     await handler(alert)
#                 else:
#                     handler(alert)
#             except Exception as e:
#                 logger.error("Alert handler failed", error=str(e))
    
#     def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
#         """Get recent alerts"""
#         return self._alert_history[-limit:]
    
#     def clear_alerts(self):
#         """Clear alert history"""
#         self._alert_history.clear()


# # Global metrics instance
# _global_metrics: Optional[MetricsCollector] = None


# def get_metrics_collector() -> MetricsCollector:
#     """Get or create global metrics collector"""
#     global _global_metrics
#     if _global_metrics is None:
#         _global_metrics = MetricsCollector()
#     return _global_metrics


# def setup_monitoring(registry: Optional[CollectorRegistry] = None) -> tuple[MetricsCollector, PerformanceMonitor, AlertManager]:
#     """Setup monitoring components"""
#     metrics = MetricsCollector(registry)
#     performance_monitor = PerformanceMonitor(metrics)
#     alert_manager = AlertManager(metrics)
    
#     return metrics, performance_monitor, alert_manager



# odc/monitoring/metrics.py

"""Metrics and monitoring for SAP OData connector"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import structlog
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, push_to_gateway
from datetime import datetime, timezone
import socket

logger = structlog.get_logger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class ConnectorMetrics:
    """
    Container for all connector metrics.
    This is now just a data structure to hold the metric objects.
    """
    requests_total: Counter
    request_duration: Histogram
    records_processed: Counter
    transformation_duration: Histogram
    queue_size: Gauge
    active_workers: Gauge
    errors_total: Counter
    circuit_breaker_state: Gauge
    storage_operations: Counter
    storage_duration: Histogram


class MetricsCollector:
    """Collects and manages metrics for the SAP OData connector"""
    
    def __init__(
        self, 
        registry: Optional[CollectorRegistry] = None,
        pushgateway_url: Optional[str] = None,
        job_name: str = "sap_odata_connector",
        instance_name: Optional[str] = None,
        auto_push: bool = False
    ):
        # Each collector instance gets its own registry to avoid global conflicts.
        self.registry = registry or CollectorRegistry()
        self.metrics = self._create_all_metrics()
        self._start_time = time.time()
        self._custom_metrics: Dict[str, Any] = {}
        
        # Prometheus Pushgateway configuration
        self.pushgateway_url = pushgateway_url
        self.job_name = job_name
        self.instance_name = instance_name or self._get_default_instance_name()
        self.auto_push = auto_push
        self._last_push_time = 0
        self._push_interval = 10  # seconds

    def _create_all_metrics(self) -> ConnectorMetrics:
        """Creates all metric objects, assigning them to our specific registry."""
        return ConnectorMetrics(
            requests_total=Counter(
                'sap_odata_requests_total',
                'Total number of OData requests',
                ['entity', 'status', 'worker_id'],
                registry=self.registry
            ),
            request_duration=Histogram(
                'sap_odata_request_duration_seconds',
                'Request duration in seconds',
                ['entity', 'worker_id'],
                registry=self.registry
            ),
            records_processed=Counter(
                'sap_odata_records_processed_total',
                'Total number of records processed',
                ['entity', 'status'],
                registry=self.registry
            ),
            transformation_duration=Histogram(
                'sap_odata_transformation_duration_seconds',
                'Transformation duration in seconds',
                ['entity'],
                registry=self.registry
            ),
            queue_size=Gauge(
                'sap_odata_queue_size',
                'Current queue size',
                registry=self.registry
            ),
            active_workers=Gauge(
                'sap_odata_active_workers',
                'Number of active workers',
                registry=self.registry
            ),
            errors_total=Counter(
                'sap_odata_errors_total',
                'Total number of errors',
                ['entity', 'error_type', 'worker_id'],
                registry=self.registry
            ),
            circuit_breaker_state=Gauge(
                'sap_odata_circuit_breaker_state',
                'Circuit breaker state (0=closed, 1=open, 2=half_open)',
                ['worker_id'],
                registry=self.registry
            ),
            storage_operations=Counter(
                'sap_odata_storage_operations_total',
                'Total storage operations',
                ['storage_type', 'operation', 'status'],
                registry=self.registry
            ),
            storage_duration=Histogram(
                'sap_odata_storage_duration_seconds',
                'Storage operation duration',
                ['storage_type', 'operation'],
                registry=self.registry
            )
        )

    def record_request(
        self,
        entity: str,
        worker_id: str,
        duration: float,
        success: bool,
        error_type: Optional[str] = None
    ):
        """Record a request metric"""
        status = "success" if success else "error"
        
        self.metrics.requests_total.labels(
            entity=entity,
            status=status,
            worker_id=worker_id
        ).inc()
        
        self.metrics.request_duration.labels(
            entity=entity,
            worker_id=worker_id
        ).observe(duration)
        
        if not success and error_type:
            self.metrics.errors_total.labels(
                entity=entity,
                error_type=error_type,
                worker_id=worker_id
            ).inc()
        
        # Auto-push metrics if enabled
        self._auto_push_if_enabled()
    
    def record_records_processed(
        self,
        entity: str,
        count: int,
        success: bool
    ):
        """Record processed records metric"""
        status = "success" if success else "error"
        
        self.metrics.records_processed.labels(
            entity=entity,
            status=status
        ).inc(count)
        
        # Auto-push metrics if enabled
        self._auto_push_if_enabled()
    
    def record_transformation(
        self,
        entity: str,
        duration: float
    ):
        """Record transformation metric"""
        self.metrics.transformation_duration.labels(
            entity=entity
        ).observe(duration)
    
    def update_queue_size(self, size: int):
        """Update queue size metric"""
        self.metrics.queue_size.set(size)
    
    def update_active_workers(self, count: int):
        """Update active workers metric"""
        self.metrics.active_workers.set(count)
    
    def update_circuit_breaker_state(
        self,
        worker_id: str,
        state: str
    ):
        """Update circuit breaker state metric"""
        state_mapping = {
            'closed': 0,
            'open': 1,
            'half_open': 2
        }
        
        self.metrics.circuit_breaker_state.labels(
            worker_id=worker_id
        ).set(state_mapping.get(state, 0))
    
    def record_storage_operation(
        self,
        storage_type: str,
        operation: str,
        duration: float,
        success: bool
    ):
        """Record storage operation metric"""
        status = "success" if success else "error"
        
        self.metrics.storage_operations.labels(
            storage_type=storage_type,
            operation=operation,
            status=status
        ).inc()
        
        self.metrics.storage_duration.labels(
            storage_type=storage_type,
            operation=operation
        ).observe(duration)
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format"""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        uptime = time.time() - self._start_time
        
        return {
            'uptime_seconds': uptime,
            'uptime_formatted': self._format_duration(uptime),
            'start_time': datetime.fromtimestamp(self._start_time, tz=timezone.utc).isoformat(),
            'current_time': datetime.now(timezone.utc).isoformat()
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _get_default_instance_name(self) -> str:
        """Generate a default instance name based on hostname"""
        try:
            return socket.gethostname()
        except:
            return "unknown"
    
    def push_metrics(self, force: bool = False):
        """
        Push metrics to Prometheus Pushgateway.
        
        Args:
            force: Force push even if interval hasn't elapsed
        """
        if not self.pushgateway_url:
            logger.debug("Pushgateway URL not configured, skipping metrics push")
            return
        
        current_time = time.time()
        
        # Check if we should push based on interval (unless forced)
        if not force and (current_time - self._last_push_time) < self._push_interval:
            return
        
        try:
            # Push metrics to Pushgateway
            push_to_gateway(
                gateway=self.pushgateway_url,
                job=self.job_name,
                registry=self.registry,
                grouping_key={'instance': self.instance_name}
            )
            
            self._last_push_time = current_time
            logger.debug(
                "Metrics pushed to Prometheus Pushgateway",
                pushgateway_url=self.pushgateway_url,
                job=self.job_name,
                instance=self.instance_name
            )
            
        except Exception as e:
            logger.warning(
                "Failed to push metrics to Prometheus Pushgateway",
                error=str(e),
                pushgateway_url=self.pushgateway_url
            )
    
    def _auto_push_if_enabled(self):
        """Automatically push metrics if auto_push is enabled"""
        if self.auto_push:
            self.push_metrics()


class PerformanceMonitor:
    """Monitors performance and health of the connector"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._health_checks: Dict[str, Callable] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._thresholds = {
            'error_rate_threshold': 0.1,  # 10%
            'avg_response_time_threshold': 30.0,  # 30 seconds
            'queue_size_threshold': 1000
        }
    
    def add_health_check(self, name: str, check_func: Callable):
        """Add a health check function"""
        self._health_checks[name] = check_func
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_healthy = True
        
        for name, check_func in self._health_checks.items():
            try:
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                results[name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'result': result
                }
                if not result:
                    overall_healthy = False
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e)
                }
                overall_healthy = False
        
        results['overall'] = 'healthy' if overall_healthy else 'unhealthy'
        return results
    
    def check_performance_thresholds(self) -> List[Dict[str, Any]]:
        """Check if performance metrics exceed thresholds"""
        alerts = []
        
        # This would typically query the actual metric values
        # For now, we'll return the structure
        
        return alerts
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            'thresholds': self._thresholds,
            'recent_alerts': self._alerts[-10:],  # Last 10 alerts
            'health_status': 'monitoring'
        }


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._alert_handlers: List[Callable] = []
        self._alert_history: List[Dict[str, Any]] = []
    
    def add_alert_handler(self, handler: Callable):
        """Add an alert handler function"""
        self._alert_handlers.append(handler)
    
    async def trigger_alert(
        self,
        severity: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Trigger an alert"""
        alert = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'severity': severity,
            'title': title,
            'message': message,
            'metadata': metadata or {}
        }
        
        self._alert_history.append(alert)
        
        # Keep only last 1000 alerts
        if len(self._alert_history) > 1000:
            self._alert_history = self._alert_history[-1000:]
        
        logger.warning("Alert triggered",
                       severity=severity,
                       title=title,
                       message=message)
        
        # Call alert handlers
        for handler in self._alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error("Alert handler failed", error=str(e))
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return self._alert_history[-limit:]
    
    def clear_alerts(self):
        """Clear alert history"""
        self._alert_history.clear()


# --- SINGLETON PATTERN TO ENSURE MONITORING IS INITIALIZED ONLY ONCE ---
_global_monitoring_setup: Optional[tuple] = None

def setup_monitoring(registry: Optional[CollectorRegistry] = None) -> tuple[MetricsCollector, PerformanceMonitor, AlertManager]:
    """Setup monitoring components. This is now idempotent to prevent re-creation."""
    global _global_monitoring_setup
    if _global_monitoring_setup is None:
        metrics = MetricsCollector(registry)
        performance_monitor = PerformanceMonitor(metrics)
        alert_manager = AlertManager(metrics)
        _global_monitoring_setup = (metrics, performance_monitor, alert_manager)
    return _global_monitoring_setup

def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector by ensuring setup is called."""
    metrics, _, _ = setup_monitoring()
    return metrics