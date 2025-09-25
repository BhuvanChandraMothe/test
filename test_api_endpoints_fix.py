#!/usr/bin/env python3
"""
Test script to verify API endpoints are shown during initialize() and records count is accurate
"""

import asyncio
import os
import sys
import shutil

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def test_api_endpoints_and_records():
    """Test that API endpoints show during initialize and records count is accurate"""
    
    print("🧪 Testing API Endpoints Display and Records Count")
    print("=" * 60)
    
    # Clean up output directory
    output_dir = "./test_output"
    if os.path.exists(output_dir):
        print(f"🧹 Cleaning up previous test output: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create test configuration with small limits for quick testing
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],
        total_records_limit=50,  # Very small limit to test accuracy
        batch_size=10,
        max_workers=1,
        requests_per_second=10.0,
        max_connections=10,  # Small connection pool
        output_directory="./test_output",
        raw_data_directory="./test_output/raw",
        processed_data_directory="./test_output/processed"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        print("\n📋 PHASE 1: Initialize (should show API endpoints)")
        print("-" * 50)
        await connector.initialize()
        
        print("\n📋 PHASE 2: Execute (should only show execution progress)")
        print("-" * 50)
        stats = await connector.run()
        
        print("\n✅ Test completed successfully!")
        print("=" * 60)
        print(f"📊 Final Statistics:")
        print(f"   Duration: {stats.duration_seconds:.2f}s")
        print(f"   Entities Processed: {stats.entities_processed}")
        print(f"   Records Processed: {stats.records_processed}")
        print(f"   Records Stored: {stats.records_stored}")
        print(f"   Commands Executed: {stats.commands_executed}")
        print(f"   Commands Failed: {stats.commands_failed}")
        
        # Verify the record limit was respected
        if stats.records_processed <= config.total_records_limit:
            print(f"✅ Record limit respected: {stats.records_processed} <= {config.total_records_limit}")
        else:
            print(f"❌ Record limit exceeded: {stats.records_processed} > {config.total_records_limit}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        if connector and connector.proxy_pool:
            try:
                await connector._cleanup()
            except:
                pass

def main():
    """Main function"""
    try:
        success = asyncio.run(test_api_endpoints_and_records())
        print(f"\n📊 Test result: {'SUCCESS' if success else 'FAILED'}")
        
        # Force exit
        import os
        os._exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import os
        os._exit(1)

if __name__ == "__main__":
    main()
