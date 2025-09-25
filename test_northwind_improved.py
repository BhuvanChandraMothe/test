#!/usr/bin/env python3
"""
Improved test script for SAP OData Connector with Northwind service
Includes better error handling and guaranteed stats display
"""

import asyncio
import os
import shutil
import sys
import signal
from pathlib import Path

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

# Global variables for cleanup
connector = None
stats = None

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    print(f"\n⚠️ Received signal {signum}. Attempting graceful shutdown...")
    if connector and hasattr(connector, 'proxy_pool') and connector.proxy_pool:
        print("🛑 Stopping proxy pool...")
        # Note: We can't await in signal handler, so we'll let the finally block handle cleanup
    sys.exit(1)

async def test_northwind():
    """Test the connector with Northwind service and push metrics"""
    global connector, stats
    
    print("🚀 Testing SAP OData Connector with Northwind service")
    print("=" * 60)
    
    # Get the global metrics collector instance
    metrics_collector = get_metrics_collector()

    # Clean up output directory from previous runs
    output_dir = "./test_output"
    if os.path.exists(output_dir):
        print(f"🧹 Cleaning up previous test output: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create test configuration
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],  # Process all entities
        total_records_limit=None,  # No limit for full test
        batch_size=500,
        max_workers=3,
        requests_per_second=10.0,
        output_directory="./test_output",
        raw_data_directory="./test_output/raw",
        processed_data_directory="./test_output/processed"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    # Setup progress callback for real-time updates
    def progress_callback(progress):
        print(f"📊 Progress Update:")
        print(f"   Queue Size: {progress['queue_size']}")
        print(f"   Completed Entities: {progress['completed_entities']}")
        print(f"   Records Processed: {progress['records_processed']}")
        print(f"   Commands Executed: {progress['commands_executed']}")
        print(f"   Commands Failed: {progress['commands_failed']}")
        print("-" * 50)
    
    connector.on_progress_update = progress_callback
    
    try:
        print("🔧 Initializing connector...")
        await connector.initialize()
        
        print("📋 Starting data extraction...")
        print("   Service URL: https://services.odata.org/V4/Northwind/Northwind.svc")
        print("   Output Directory: ./test_output")
        print("-" * 50)
        
        # Run the connector
        stats = await connector.run()
        
        # Force display of final statistics
        print("\n" + "=" * 60)
        print("✅ EXTRACTION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📈 Final Statistics:")
        print(f"   Duration: {stats.duration_seconds:.2f} seconds")
        print(f"   Entities Processed: {stats.entities_processed}")
        print(f"   Records Processed: {stats.records_processed}")
        print(f"   Records Stored: {stats.records_stored}")
        print(f"   Commands Executed: {stats.commands_executed}")
        print(f"   Commands Failed: {stats.commands_failed}")
        
        # Get execution summary
        summary = connector.get_execution_summary()
        print(f"\n📊 Execution Summary:")
        print(f"   Dead Letter Queue Size: {summary['dead_letter_queue']['current_size']}")
        
        if summary.get('transformation_stats'):
            trans_stats = summary['transformation_stats']
            print(f"   Transformation Success Rate: {trans_stats.records_transformed}/{trans_stats.records_processed}")
        
        # Show output files
        output_path = Path("./test_output")
        if output_path.exists():
            print(f"\n📁 Output files created in {output_path}:")
            for file_path in output_path.rglob("*"):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"   - {file_path.relative_to(output_path)} ({size:,} bytes)")
        
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
        
        print("\n🎉 Test completed successfully!")
        print("=" * 60)
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Ensure cleanup happens regardless of how we exit
        print("\n🧹 Cleaning up resources...")
        if connector and hasattr(connector, 'proxy_pool') and connector.proxy_pool:
            try:
                if connector.proxy_pool.is_running:
                    await connector.proxy_pool.stop()
                    print("✅ Proxy pool stopped successfully")
            except Exception as e:
                print(f"⚠️ Error during cleanup: {e}")
        
        # Display stats even if there was an error
        if stats:
            print(f"\n📊 Final Stats (from cleanup):")
            print(f"   Duration: {stats.duration_seconds:.2f}s")
            print(f"   Records Processed: {stats.records_processed}")
            print(f"   Commands Executed: {stats.commands_executed}")


def main():
    """Main entry point with signal handling"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the async test
        success = asyncio.run(test_northwind())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Program interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Program failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
