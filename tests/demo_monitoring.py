#!/usr/bin/env python3
"""
Demo script to show Prometheus metrics and structured logging
"""

import sys
sys.path.append('.')

from odc.monitoring.metrics import MetricsCollector
from prometheus_client import CollectorRegistry, generate_latest
import structlog
import asyncio
import json
from datetime import datetime

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("sap_odata_demo")

def main():
    """Demonstrate metrics and logging"""
    
    logger.info("Starting SAP OData Connector monitoring demo")
    
    # Create metrics collector
    registry = CollectorRegistry()
    metrics = MetricsCollector(registry)
    
    # Simulate some connector activity
    logger.info("Recording sample metrics")
    
    # Record requests
    metrics.record_request("Products", "worker_1", 1.2, True)
    metrics.record_request("Orders", "worker_2", 0.8, True) 
    metrics.record_request("Categories", "worker_1", 2.1, False, "timeout")
    
    logger.info("Request recorded", entity="Products", duration=1.2, success=True)
    logger.info("Request recorded", entity="Orders", duration=0.8, success=True)
    logger.error("Request failed", entity="Categories", duration=2.1, error="timeout")
    
    # Record processing
    metrics.record_records_processed("Products", 150, True)
    metrics.record_records_processed("Orders", 89, True)
    
    logger.info("Records processed", entity="Products", count=150)
    logger.info("Records processed", entity="Orders", count=89)
    
    # Update gauges
    metrics.update_queue_size(12)
    metrics.update_active_workers(3)
    
    logger.info("System status", queue_size=12, active_workers=3)
    
    # Show Prometheus metrics
    print("\n" + "="*60)
    print("PROMETHEUS METRICS (Prometheus format)")
    print("="*60)
    
    prometheus_output = generate_latest(registry).decode('utf-8')
    print(prometheus_output)
    
    # Show summary stats
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    stats = metrics.get_summary_stats()
    for key, value in stats.items():
        print(f"{key:20}: {value}")
    
    logger.info("Demo completed successfully")

if __name__ == "__main__":
    main()
