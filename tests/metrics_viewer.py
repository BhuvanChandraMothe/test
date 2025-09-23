#!/usr/bin/env python3
"""
View Prometheus metrics and logs from SAP OData Connector
"""

import sys
sys.path.append('.')

from odc.monitoring.metrics import MetricsCollector
from prometheus_client import CollectorRegistry, generate_latest
import time

def show_prometheus_metrics():
    """Show Prometheus metrics in standard format"""
    
    # Create metrics collector
    registry = CollectorRegistry()
    metrics = MetricsCollector(registry)
    
    print("Simulating SAP OData Connector activity...")
    
    # Simulate connector metrics
    metrics.record_request("Products", "worker_1", 1.2, True)
    metrics.record_request("Orders", "worker_2", 0.8, True) 
    metrics.record_request("Categories", "worker_1", 2.1, False, "timeout")
    metrics.record_request("Suppliers", "worker_3", 0.5, True)
    
    metrics.record_records_processed("Products", 150, True)
    metrics.record_records_processed("Orders", 89, True)
    
    metrics.update_queue_size(12)
    metrics.update_active_workers(3)
    
    metrics.record_storage_operation("local_file", "write", 0.3, True)
    metrics.record_storage_operation("local_file", "read", 0.1, True)
    
    # Generate Prometheus format output
    prometheus_text = generate_latest(registry).decode('utf-8')
    
    print("\n" + "="*80)
    print("PROMETHEUS METRICS OUTPUT")
    print("="*80)
    print(prometheus_text)
    
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    stats = metrics.get_summary_stats()
    for key, value in stats.items():
        print(f"{key:25}: {value}")
    
    print("\n" + "="*80)
    print("HOW TO USE THESE METRICS")
    print("="*80)
    print("1. Prometheus Server: Configure Prometheus to scrape these metrics")
    print("2. Grafana Dashboard: Create visualizations from these metrics")
    print("3. Alerting: Set up alerts based on error rates, latency, etc.")
    print("4. HTTP Endpoint: Expose /metrics endpoint in your web server")

if __name__ == "__main__":
    show_prometheus_metrics()
