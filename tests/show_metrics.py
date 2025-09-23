#!/usr/bin/env python3
"""
Simple script to demonstrate Prometheus metrics and logging in SAP OData Connector
"""

import sys
import os
sys.path.append('.')

from odc.monitoring.metrics import MetricsCollector, setup_monitoring
import asyncio
import structlog

# Configure structlog for better log output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

async def demonstrate_metrics():
    """Demonstrate metrics collection and logging"""
    
    logger.info("Starting metrics demonstration")
    
    # Setup monitoring components
    metrics, perf_monitor, alert_manager = setup_monitoring()
    
    # Simulate connector activity
    logger.info("Simulating OData requests")
    
    # Record successful requests
    metrics.record_request("Products", "worker_1", 1.2, True)
    metrics.record_request("Orders", "worker_2", 0.8, True)
    metrics.record_request("Customers", "worker_3", 0.5, True)
    
    # Record failed request
    metrics.record_request("Categories", "worker_1", 2.1, False, "timeout")
    
    # Record processing metrics
    metrics.record_records_processed("Products", 150, True)
    metrics.record_records_processed("Orders", 89, True)
    
    # Update system metrics
    metrics.update_queue_size(12)
    metrics.update_active_workers(3)
    
    # Record storage operations
    metrics.record_storage_operation("local_file", "write", 0.3, True)
    metrics.record_storage_operation("local_file", "read", 0.1, True)
    
    logger.info("Metrics recorded", 
                active_workers=3, 
                queue_size=12,
                total_requests=4)
    
    print("\n" + "="*50)
    print("PROMETHEUS METRICS OUTPUT")
    print("="*50)
    print(metrics.get_metrics_text())
    
    print("\n" + "="*50)
    print("SUMMARY STATISTICS")
    print("="*50)
    stats = metrics.get_summary_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Demonstrate alert
    logger.warning("Demonstrating alert system")
    await alert_manager.trigger_alert(
        severity="warning",
        title="High Error Rate",
        message="Error rate exceeded 10% threshold",
        metadata={"error_rate": 0.25, "entity": "Categories"}
    )
    
    # Show recent alerts
    print("\n" + "="*50)
    print("RECENT ALERTS")
    print("="*50)
    recent_alerts = alert_manager.get_recent_alerts(5)
    for alert in recent_alerts:
        print(f"[{alert['severity'].upper()}] {alert['title']}: {alert['message']}")
        print(f"  Time: {alert['timestamp']}")
        if alert['metadata']:
            print(f"  Metadata: {alert['metadata']}")
    
    logger.info("Metrics demonstration completed")

if __name__ == "__main__":
    asyncio.run(demonstrate_metrics())
