#!/usr/bin/env python3
"""
Test script with proper timeout and termination handling
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

# Global variables for cleanup
connector = None
main_task = None

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    print(f"\n⚠️ Received signal {signum}. Forcing exit...")
    if main_task:
        main_task.cancel()
    sys.exit(1)

async def test_with_timeout():
    """Test the connector with timeout protection"""
    global connector
    
    print("🚀 Testing SAP OData Connector with timeout protection")
    print("=" * 60)

    # Clean up output directory from previous runs
    output_dir = "./test_output"
    if os.path.exists(output_dir):
        print(f"🧹 Cleaning up previous test output: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create test configuration with limits
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],  # Process all entities
        total_records_limit=1000,  # Limit total records for faster completion
        batch_size=100,
        max_workers=2,  # Reduce workers to avoid overwhelming
        requests_per_second=5.0,
        output_directory="./test_output",
        raw_data_directory="./test_output/raw",
        processed_data_directory="./test_output/processed"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        print("🔧 Initializing connector...")
        await connector.initialize()
        
        print("📋 Starting data extraction with timeout protection...")
        
        # Run with timeout protection
        try:
            stats = await asyncio.wait_for(connector.run(), timeout=180.0)  # 3 minute timeout
            
            # Display final statistics
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
            
            # Show output files
            output_path = Path("./test_output")
            if output_path.exists():
                print(f"\n📁 Output files created:")
                file_count = 0
                total_size = 0
                for file_path in output_path.rglob("*"):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        total_size += size
                        file_count += 1
                print(f"   Total files: {file_count}")
                print(f"   Total size: {total_size:,} bytes")
            
            print("\n🎉 Test completed successfully!")
            return True
            
        except asyncio.TimeoutError:
            print("\n⏰ Test timed out - forcing completion")
            print("   This prevents the process from hanging indefinitely")
            return False
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Ensure cleanup happens
        print("\n🧹 Performing cleanup...")
        if connector:
            try:
                await connector._cleanup()
                print("✅ Cleanup completed successfully")
            except Exception as e:
                print(f"⚠️ Error during cleanup: {e}")

async def main():
    """Main entry point with timeout protection"""
    global main_task
    main_task = asyncio.current_task()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = await test_with_timeout()
        print(f"\n📊 Test result: {'SUCCESS' if success else 'FAILED/TIMEOUT'}")
        return success
    except asyncio.CancelledError:
        print("\n⚠️ Test was cancelled")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Program interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Program failed: {e}")
        sys.exit(1)
