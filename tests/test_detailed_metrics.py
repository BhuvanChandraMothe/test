#!/usr/bin/env python3
"""
Comprehensive test to verify detailed SAP OData connector metrics are working properly
"""

import sys
import os
sys.path.append('.')

import asyncio
import structlog
from odc.monitoring.metrics import MetricsCollector, get_metrics_collector
from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector
from prometheus_client import CollectorRegistry, generate_latest, push_to_gateway

# Setup logging
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

async def test_detailed_metrics():
    """Test that detailed metrics are properly recorded during connector operations"""
    
    print("\n" + "="*70)
    print("TESTING DETAILED SAP ODATA CONNECTOR METRICS")
    print("="*70)
    
    # Get the global metrics collector
    metrics = get_metrics_collector()
    
    print(f"✓ Global metrics collector: {metrics}")
    print(f"✓ Registry: {metrics.registry}")
    
    # Test 1: Simulate worker operations with detailed metrics
    print("\n1. Testing Worker Operation Metrics...")
    
    # Simulate multiple worker requests
    entities = ["Products", "Orders", "Customers", "Categories"]
    workers = ["worker_0", "worker_1", "worker_2"]
    
    for i, entity in enumerate(entities):
        worker_id = workers[i % len(workers)]
        
        # Successful request
        metrics.record_request(
            entity=entity,
            worker_id=worker_id,
            duration=1.2 + (i * 0.3),
            success=True
        )
        
        # Record processed records
        metrics.record_records_processed(
            entity=entity,
            count=50 + (i * 25),
            success=True
        )
        
        # Record transformation
        metrics.record_transformation(
            entity=entity,
            duration=0.5 + (i * 0.1)
        )
        
        # Record storage operation
        metrics.record_storage_operation(
            storage_type="local_file",
            operation="write",
            duration=0.3 + (i * 0.05),
            success=True
        )
    
    # Simulate some failed operations
    metrics.record_request("Categories", "worker_1", 3.5, False, "timeout")
    metrics.record_records_processed("Categories", 0, False)
    metrics.record_storage_operation("local_file", "write", 0.1, False)
    
    # Update system metrics
    metrics.update_queue_size(15)
    metrics.update_active_workers(3)
    metrics.update_circuit_breaker_state("worker_0", "closed")
    metrics.update_circuit_breaker_state("worker_1", "open")
    
    print("✓ Recorded detailed metrics for multiple entities and workers")
    
    # Test 2: Generate and analyze metrics output
    print("\n2. Analyzing Metrics Output...")
    
    try:
        metrics_text = metrics.get_metrics_text()
        print(f"✓ Generated metrics text: {len(metrics_text)} characters")
        
        # Parse and count different metric types
        lines = metrics_text.split('\n')
        metric_counts = {}
        
        for line in lines:
            if line.startswith('sap_odata_') and '{' in line:
                metric_name = line.split('{')[0]
                metric_counts[metric_name] = metric_counts.get(metric_name, 0) + 1
        
        print("\nDetailed Metrics Found:")
        for metric_name, count in sorted(metric_counts.items()):
            print(f"  {metric_name}: {count} entries")
        
        # Check for key metrics
        required_metrics = [
            'sap_odata_requests_total',
            'sap_odata_request_duration_seconds',
            'sap_odata_records_processed_total',
            'sap_odata_transformation_duration_seconds',
            'sap_odata_queue_size',
            'sap_odata_active_workers',
            'sap_odata_errors_total',
            'sap_odata_storage_operations_total',
            'sap_odata_storage_duration_seconds',
            'sap_odata_circuit_breaker_state'
        ]
        
        missing_metrics = []
        for required in required_metrics:
            if required not in metric_counts:
                missing_metrics.append(required)
        
        if missing_metrics:
            print(f"\n❌ MISSING METRICS: {missing_metrics}")
            return False
        else:
            print(f"\n✅ ALL REQUIRED METRICS PRESENT!")
        
    except Exception as e:
        print(f"❌ Error generating metrics: {e}")
        return False
    
    # Test 3: Verify metric labels and values
    print("\n3. Verifying Metric Labels and Values...")
    
    # Check for entity-specific metrics
    entity_metrics = [line for line in lines if 'entity=' in line]
    worker_metrics = [line for line in lines if 'worker_id=' in line]
    
    print(f"✓ Entity-labeled metrics: {len(entity_metrics)}")
    print(f"✓ Worker-labeled metrics: {len(worker_metrics)}")
    
    # Show sample metrics with labels
    print("\nSample Detailed Metrics:")
    sample_count = 0
    for line in lines:
        if 'sap_odata_' in line and '{' in line and sample_count < 10:
            print(f"  {line}")
            sample_count += 1
    
    # Test 4: Simulate Push Gateway preparation
    print("\n4. Testing Push Gateway Preparation...")
    
    try:
        # This would be the data sent to Push Gateway
        push_data = generate_latest(metrics.registry).decode('utf-8')
        push_lines = push_data.split('\n')
        
        # Count metrics ready for push
        push_metrics = {}
        for line in push_lines:
            if line.startswith('sap_odata_'):
                metric_name = line.split('{')[0] if '{' in line else line.split(' ')[0]
                push_metrics[metric_name] = push_metrics.get(metric_name, 0) + 1
        
        print(f"✓ Metrics ready for Push Gateway: {len(push_metrics)} types")
        print(f"✓ Total metric entries: {sum(push_metrics.values())}")
        
        if sum(push_metrics.values()) > 0:
            print("✅ Push Gateway data is ready with detailed metrics!")
        else:
            print("❌ No metrics ready for Push Gateway!")
            return False
            
    except Exception as e:
        print(f"❌ Error preparing Push Gateway data: {e}")
        return False
    
    # Test 5: Summary statistics
    print("\n5. Summary Statistics...")
    
    try:
        stats = metrics.get_summary_stats()
        print("✓ Summary statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ Error getting summary stats: {e}")
    
    return True

async def test_connector_integration():
    """Test metrics integration with actual connector (if possible)"""
    
    print("\n" + "="*70)
    print("TESTING CONNECTOR INTEGRATION")
    print("="*70)
    
    try:
        # Create a minimal config for testing
        config = ClientConfig(
            odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
            batch_size=10,
            max_workers=2,
            total_records_limit=20
        )
        
        print("✓ Created test configuration")
        
        # Create connector instance
        connector = SAPODataConnector(config)
        print("✓ Created connector instance")
        
        # Check that metrics are properly initialized
        await connector.initialize()
        print("✓ Connector initialized")
        
        if connector.metrics:
            print("✅ Connector has metrics collector!")
            print(f"  Metrics instance: {connector.metrics}")
            print(f"  Same as global: {connector.metrics is get_metrics_collector()}")
        else:
            print("❌ Connector missing metrics collector!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Connector integration test failed: {e}")
        return False

async def main():
    """Main test function"""
    
    print("SAP OData Connector Detailed Metrics Test")
    print("="*70)
    
    # Test detailed metrics functionality
    metrics_test_passed = await test_detailed_metrics()
    
    # Test connector integration
    integration_test_passed = await test_connector_integration()
    
    # Final summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    print(f"✓ Detailed Metrics Test: {'PASS' if metrics_test_passed else 'FAIL'}")
    print(f"✓ Connector Integration: {'PASS' if integration_test_passed else 'FAIL'}")
    
    if metrics_test_passed and integration_test_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Detailed SAP OData connector metrics are working correctly!")
        print("✅ Metrics include:")
        print("   - Request metrics with entity and worker labels")
        print("   - Processing and transformation metrics")
        print("   - Queue size and active worker metrics")
        print("   - Error metrics with detailed error types")
        print("   - Storage operation metrics")
        print("   - Circuit breaker state metrics")
        print("\n📊 Metrics are ready for Prometheus Push Gateway!")
        
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("   Please check the error messages above for details.")
    
    # Save detailed metrics for inspection
    try:
        metrics = get_metrics_collector()
        with open('detailed_metrics_test_output.txt', 'w', encoding='utf-8') as f:
            f.write(metrics.get_metrics_text())
        print(f"\n📄 Detailed metrics saved to: detailed_metrics_test_output.txt")
    except Exception as e:
        print(f"❌ Could not save metrics output: {e}")

if __name__ == "__main__":
    asyncio.run(main())
