#!/usr/bin/env python3
"""
Simple test to isolate metrics issues
"""

import sys
import os
sys.path.append('.')

try:
    from odc.monitoring.metrics import MetricsCollector
    from prometheus_client import CollectorRegistry, generate_latest
    
    print("Creating metrics collector...")
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)
    
    print("Recording test metrics...")
    collector.record_request("Products", "worker_1", 1.5, True)
    collector.update_queue_size(10)
    collector.update_active_workers(3)
    
    print("Generating metrics text...")
    metrics_text = collector.get_metrics_text()
    
    print("SUCCESS: Metrics generated")
    print(f"Length: {len(metrics_text)} characters")
    
    # Show key metrics
    lines = metrics_text.split('\n')
    for line in lines:
        if 'sap_odata' in line and not line.startswith('#'):
            print(f"METRIC: {line}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
