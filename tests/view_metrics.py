#!/usr/bin/env python3
"""
Script to view Prometheus metrics from the SAP OData Connector
"""

import asyncio
import time
from odc.monitoring.metrics import MetricsCollector, setup_monitoring

async def main():
    """View current metrics"""
    
    # Setup monitoring
    metrics, performance_monitor, alert_manager = setup_monitoring()
    
    # Simulate some metrics (in real usage, these come from the connector)
    metrics.record_request("Products", "worker_1", 1.2, True)
    metrics.record_request("Orders", "worker_2", 0.8, True)
    metrics.record_request("Categories", "worker_1", 2.1, False, "timeout")
    
    metrics.record_records_processed("Products", 150, True)
    metrics.record_records_processed("Orders", 89, True)
    
    metrics.update_queue_size(12)
    metrics.update_active_workers(3)
    
    # Get metrics in Prometheus format
    print("=== PROMETHEUS METRICS ===")
    print(metrics.get_metrics_text())
    
    print("\n=== SUMMARY STATISTICS ===")
    summary = metrics.get_summary_stats()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # Run health checks
    print("\n=== HEALTH CHECKS ===")
    
    # Add some sample health checks
    performance_monitor.add_health_check("database", lambda: True)
    performance_monitor.add_health_check("odata_service", lambda: True)
    
    health_results = await performance_monitor.run_health_checks()
    for check, result in health_results.items():
        print(f"{check}: {result}")

if __name__ == "__main__":
    asyncio.run(main())
