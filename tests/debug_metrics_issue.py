#!/usr/bin/env python3
"""
Debug script to identify and fix missing SAP OData connector metrics in Prometheus
"""

import sys
import os
sys.path.append('.')

from odc.monitoring.metrics import MetricsCollector, setup_monitoring
from prometheus_client import CollectorRegistry, generate_latest, push_to_gateway
import asyncio
import structlog
import time

# Setup basic logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

def test_metrics_creation():
    """Test if metrics are properly created and registered"""
    print("\n" + "="*60)
    print("TESTING METRICS CREATION AND REGISTRATION")
    print("="*60)
    
    # Create a fresh registry for testing
    test_registry = CollectorRegistry()
    metrics_collector = MetricsCollector(registry=test_registry)
    
    print(f"Registry created: {test_registry}")
    print(f"Metrics collector created: {metrics_collector}")
    print(f"Number of collectors in registry: {len(list(test_registry._collector_to_names.keys()))}")
    
    # List all registered metrics
    print("\nRegistered metrics:")
    for collector in test_registry._collector_to_names.keys():
        names = test_registry._collector_to_names[collector]
        print(f"  - {collector.__class__.__name__}: {names}")
    
    return metrics_collector, test_registry

def test_metrics_recording(metrics_collector):
    """Test recording various metrics"""
    print("\n" + "="*60)
    print("TESTING METRICS RECORDING")
    print("="*60)
    
    # Record different types of metrics
    print("Recording request metrics...")
    metrics_collector.record_request("Products", "worker_1", 1.5, True)
    metrics_collector.record_request("Orders", "worker_2", 2.1, False, "timeout")
    
    print("Recording processing metrics...")
    metrics_collector.record_records_processed("Products", 100, True)
    metrics_collector.record_records_processed("Orders", 50, False)
    
    print("Recording transformation metrics...")
    metrics_collector.record_transformation("Products", 0.8)
    
    print("Updating system metrics...")
    metrics_collector.update_queue_size(25)
    metrics_collector.update_active_workers(4)
    
    print("Recording storage operations...")
    metrics_collector.record_storage_operation("local_file", "write", 0.5, True)
    metrics_collector.record_storage_operation("local_file", "read", 0.2, True)
    
    print("Recording circuit breaker state...")
    metrics_collector.update_circuit_breaker_state("worker_1", "closed")
    metrics_collector.update_circuit_breaker_state("worker_2", "open")
    
    print("All metrics recorded successfully!")

def test_metrics_output(metrics_collector):
    """Test metrics output in Prometheus format"""
    print("\n" + "="*60)
    print("TESTING METRICS OUTPUT")
    print("="*60)
    
    try:
        metrics_text = metrics_collector.get_metrics_text()
        print("Metrics text generated successfully!")
        print(f"Length: {len(metrics_text)} characters")
        
        # Show first few lines to verify content
        lines = metrics_text.split('\n')[:20]
        print("\nFirst 20 lines of metrics output:")
        for i, line in enumerate(lines, 1):
            if line.strip():  # Only show non-empty lines
                print(f"{i:2d}: {line}")
        
        # Count different metric types
        request_metrics = [line for line in metrics_text.split('\n') if 'sap_odata_requests_total' in line]
        duration_metrics = [line for line in metrics_text.split('\n') if 'sap_odata_request_duration' in line]
        records_metrics = [line for line in metrics_text.split('\n') if 'sap_odata_records_processed' in line]
        
        print(f"\nMetric counts:")
        print(f"  Request metrics: {len(request_metrics)}")
        print(f"  Duration metrics: {len(duration_metrics)}")
        print(f"  Records metrics: {len(records_metrics)}")
        
        return metrics_text
        
    except Exception as e:
        print(f"ERROR generating metrics text: {e}")
        return None

def test_push_gateway_simulation(registry):
    """Test pushing metrics to Push Gateway (simulation)"""
    print("\n" + "="*60)
    print("TESTING PUSH GATEWAY SIMULATION")
    print("="*60)
    
    # Simulate push to gateway (without actually connecting)
    try:
        # This would normally push to an actual gateway
        # For testing, we'll just verify the registry content
        print("Registry content for push gateway:")
        
        metrics_text = generate_latest(registry).decode('utf-8')
        lines = metrics_text.split('\n')
        
        # Count metrics by type
        metric_types = {}
        for line in lines:
            if line.startswith('sap_odata_'):
                metric_name = line.split('{')[0] if '{' in line else line.split(' ')[0]
                metric_types[metric_name] = metric_types.get(metric_name, 0) + 1
        
        print("Metrics ready for push gateway:")
        for metric_name, count in sorted(metric_types.items()):
            print(f"  {metric_name}: {count} entries")
        
        if not metric_types:
            print("WARNING: No SAP OData metrics found for push gateway!")
            return False
        
        print(f"\nTotal SAP OData metrics: {sum(metric_types.values())}")
        return True
        
    except Exception as e:
        print(f"ERROR in push gateway simulation: {e}")
        return False

def test_global_metrics_singleton():
    """Test the global metrics singleton pattern"""
    print("\n" + "="*60)
    print("TESTING GLOBAL METRICS SINGLETON")
    print("="*60)
    
    from odc.monitoring.metrics import get_metrics_collector
    
    # Get metrics collector multiple times
    collector1 = get_metrics_collector()
    collector2 = get_metrics_collector()
    
    print(f"Collector 1: {id(collector1)}")
    print(f"Collector 2: {id(collector2)}")
    print(f"Same instance: {collector1 is collector2}")
    
    # Test recording on global instance
    collector1.record_request("TestEntity", "test_worker", 1.0, True)
    
    # Verify it appears in both references
    metrics_text = collector2.get_metrics_text()
    has_test_metrics = 'TestEntity' in metrics_text
    print(f"Test metrics found in global collector: {has_test_metrics}")
    
    return collector1

async def main():
    """Main diagnostic function"""
    print("SAP OData Connector Metrics Diagnostic Tool")
    print("="*60)
    
    # Test 1: Metrics creation and registration
    metrics_collector, test_registry = test_metrics_creation()
    
    # Test 2: Recording metrics
    test_metrics_recording(metrics_collector)
    
    # Test 3: Metrics output
    metrics_text = test_metrics_output(metrics_collector)
    
    # Test 4: Push gateway simulation
    push_success = test_push_gateway_simulation(test_registry)
    
    # Test 5: Global singleton
    global_collector = test_global_metrics_singleton()
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    print(f"✓ Metrics creation: {'PASS' if metrics_collector else 'FAIL'}")
    print(f"✓ Metrics output: {'PASS' if metrics_text else 'FAIL'}")
    print(f"✓ Push gateway ready: {'PASS' if push_success else 'FAIL'}")
    print(f"✓ Global singleton: {'PASS' if global_collector else 'FAIL'}")
    
    if metrics_text and push_success:
        print("\n✅ DIAGNOSIS: Metrics system appears to be working correctly!")
        print("   The issue may be in how metrics are being recorded during actual connector runs.")
        print("   Check that:")
        print("   1. Metrics are being recorded in all worker operations")
        print("   2. Worker IDs are being passed correctly (not hardcoded as 'unknown')")
        print("   3. Push gateway URL is accessible")
        print("   4. Metrics are being pushed at the right time in the connector lifecycle")
    else:
        print("\n❌ DIAGNOSIS: Issues found in metrics system!")
        print("   Problems detected that need fixing before metrics will work properly.")
    
    # Save detailed metrics output for analysis
    if metrics_text:
        with open('debug_metrics_output.txt', 'w', encoding='utf-8') as f:
            f.write(metrics_text)
        print(f"\n📄 Detailed metrics output saved to: debug_metrics_output.txt")

if __name__ == "__main__":
    asyncio.run(main())
