#!/usr/bin/env python3
"""
Simple script to test pushing SAP OData connector metrics to Prometheus Push Gateway
"""

import sys
import os
sys.path.append('.')

from odc.monitoring.metrics import get_metrics_collector
from prometheus_client import push_to_gateway
import time

def test_push_metrics():
    """Test pushing metrics to Prometheus Push Gateway"""
    
    print("🧪 Testing SAP OData Connector Metrics Push to Prometheus")
    print("=" * 60)
    
    # Get metrics collector
    metrics = get_metrics_collector()
    print(f"✓ Got metrics collector: {metrics}")
    
    # Record some test metrics to make them visible
    print("\n📊 Recording test metrics...")
    
    # Simulate connector activity
    metrics.record_request("Products", "worker_1", 1.5, True)
    metrics.record_request("Orders", "worker_2", 2.1, True)
    metrics.record_request("Customers", "worker_1", 0.8, True)
    metrics.record_request("Categories", "worker_2", 3.2, False, "timeout")
    
    # Record processing metrics
    metrics.record_records_processed("Products", 150, True)
    metrics.record_records_processed("Orders", 89, True)
    metrics.record_records_processed("Customers", 45, True)
    
    # Record transformation metrics
    metrics.record_transformation("Products", 0.8)
    metrics.record_transformation("Orders", 1.2)
    
    # Update system metrics
    metrics.update_queue_size(25)
    metrics.update_active_workers(3)
    
    # Record storage operations
    metrics.record_storage_operation("local_file", "write", 0.5, True)
    metrics.record_storage_operation("local_file", "read", 0.2, True)
    metrics.record_storage_operation("local_file", "write", 0.1, False)
    
    # Update circuit breaker states
    metrics.update_circuit_breaker_state("worker_1", "closed")
    metrics.update_circuit_breaker_state("worker_2", "open")
    
    print("✓ Test metrics recorded successfully")
    
    # Show metrics before pushing
    print("\n📋 Metrics to be pushed:")
    metrics_text = metrics.get_metrics_text()
    lines = metrics_text.split('\n')
    
    # Count and show SAP OData metrics
    sap_metrics = [line for line in lines if line.startswith('sap_odata_') and '{' in line]
    print(f"✓ Found {len(sap_metrics)} SAP OData metric entries")
    
    # Show first few metrics as examples
    print("\nSample metrics:")
    for i, line in enumerate(sap_metrics[:10]):
        print(f"  {i+1}. {line}")
    
    if len(sap_metrics) > 10:
        print(f"  ... and {len(sap_metrics) - 10} more")
    
    # Push to Prometheus Push Gateway
    print(f"\n🚀 Pushing metrics to Prometheus Push Gateway...")
    
    PUSH_GATEWAY_URL = 'http://localhost:9091'
    JOB_NAME = 'sap_odata_connector_test'
    
    try:
        push_to_gateway(
            PUSH_GATEWAY_URL,
            job=JOB_NAME,
            registry=metrics.registry
        )
        print("✅ Metrics pushed successfully!")
        print(f"✓ Push Gateway URL: {PUSH_GATEWAY_URL}")
        print(f"✓ Job Name: {JOB_NAME}")
        
        print(f"\n🔍 You should now see SAP OData metrics in Prometheus!")
        print(f"📊 Check your Prometheus Push Gateway at: {PUSH_GATEWAY_URL}")
        print(f"🔎 Look for metrics starting with 'sap_odata_'")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to push metrics: {e}")
        print(f"💡 Make sure Prometheus Push Gateway is running at {PUSH_GATEWAY_URL}")
        return False

if __name__ == "__main__":
    success = test_push_metrics()
    
    if success:
        print(f"\n🎉 SUCCESS! Your SAP OData connector metrics should now be visible in Prometheus!")
        print(f"📈 Refresh your Prometheus Push Gateway page to see the new metrics.")
    else:
        print(f"\n❌ FAILED! Please check the error messages above.")
    
    sys.exit(0 if success else 1)
