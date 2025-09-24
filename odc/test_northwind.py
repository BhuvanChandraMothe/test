#!/usr/bin/env python3
"""
Test script for SAP OData Connector with Northwind service
"""

#     print("=" * 60)
    
#     # Create test configuration
#     config = ClientConfig(
#         odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
#         # public kabatte no auth
#         username=None,
#         password=None,
#         # test settings
#         selected_modules=[],  # All entities
#         total_records_limit=10,  # speed and effecienty kosam
#         batch_size=10,
#         max_workers=2,
#         requests_per_second=1.0,  #edhi set cheyyale malle (duplication kakunda)
#         # Local storage
#         output_directory="./test_output",
#         raw_data_directory="./test_output/raw",
#         processed_data_directory="./test_output/processed"
#     )
    
#     # Create connector
#     connector = SAPODataConnector(config)
    
#     # Progress tracking
#     def progress_callback(progress):
#         print(f"📊 Progress: {progress['completed_entities']} entities, "
#               f"{progress['records_processed']} records, "
#               f"Queue: {progress['queue_size']}")
    
#     connector.on_progress_update = progress_callback
    
#     try:
#         print("🚀 Initializing connector...")
#         await connector.initialize()
        
#         print("📋 Starting data extraction...")
#         stats = await connector.run()
        
#         print("\n✅ Test completed successfully!")
#         print(f"Duration: {stats.duration_seconds:.2f}s")
#         print(f"Entities: {stats.entities_processed}")
#         print(f"Records: {stats.records_processed}")
#         print(f"Stored: {stats.records_stored}")
#         print(f"Commands: {stats.commands_executed}")
#         print(f"Failures: {stats.commands_failed}")
        
#         # Show output files
#         output_dir = Path("./test_output")
#         if output_dir.exists():
#             print(f"\n📁 Output files in {output_dir}:")
#             for file_path in output_dir.rglob("*"):
#                 if file_path.is_file():
#                     size = file_path.stat().st_size
#                     print(f"  {file_path.relative_to(output_dir)} ({size} bytes)")
        
#         return True
        
#     except Exception as e:
#         print(f"\n❌ Test failed: {e}")
#         import traceback
#         traceback.print_exc()
#         return False
    
#     finally:
#         if connector.proxy_pool:
#             await connector.proxy_pool.stop()


# if __name__ == "__main__":
#     # Set up basic logging
#     import logging
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
#     # Run test
#     success = asyncio.run(test_northwind())
#     sys.exit(0 if success else 1)

import asyncio
import os
import shutil
import sys

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig
from odc.monitoring.metrics import get_metrics_collector
from prometheus_client import push_to_gateway

# Define the Push Gateway URL
PUSH_GATEWAY_URL = 'http://localhost:9091'
# Define a job name to identify this specific job in Prometheus
PROMETHEUS_JOB_NAME = 'northwind_connector'

async def test_northwind():
    """Test the connector with Northwind service and push metrics"""
    
    print("Testing SAP OData Connector with Northwind service")
    print("=" * 60)
    
    # Get the global metrics collector instance
    metrics_collector = get_metrics_collector()

    # Clean up output directory from previous runs
    output_dir = "./test_output"
    if os.path.exists(output_dir):
        print(f"Cleaning up previous test output: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create test configuration
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],
        total_records_limit=None,
        batch_size=500,
        max_workers=3,
        requests_per_second=10.0,
        output_directory="./test_output",
        raw_data_directory="./test_output/raw",
        processed_data_directory="./test_output/processed"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        print("Initializing connector...")
        await connector.initialize()
        
        print("Starting data extraction...")
        stats = await connector.run()
        
        print("\nTest completed successfully!")
        
        print("\n✅ Test completed successfully!")
        print(f"Duration: {stats.duration_seconds:.2f}s")
        print(f"Entities: {stats.entities_processed}")
        print(f"Records: {stats.records_processed}")
        print(f"Stored: {stats.records_stored}")
        print(f"Commands: {stats.commands_executed}")
        print(f"Failures: {stats.commands_failed}")
        
        print("\n📤 Pushing metrics to Prometheus Push Gateway...")
        try:
            push_to_gateway(
                PUSH_GATEWAY_URL,
                job=PROMETHEUS_JOB_NAME,
                registry=metrics_collector.registry
            )
            print("✅ Metrics pushed successfully!")
        except Exception as e:
            print(f"❌ Failed to push metrics: {e}")
            
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # This is the correct way to start an async program and ensures a clean exit
    asyncio.run(test_northwind())