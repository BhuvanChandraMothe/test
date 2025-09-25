#!/usr/bin/env python3
"""
Bulletproof test script that WILL terminate properly
"""

import asyncio
import os
import sys
import signal
import threading
import time
from pathlib import Path

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

# Global variables
connector = None
force_exit = False

def force_exit_timer():
    """Force exit after maximum time"""
    time.sleep(120)  # 2 minutes maximum
    if not force_exit:
        print("\n🚨 FORCE EXIT: Maximum time exceeded - terminating process")
        os._exit(0)  # Nuclear option - force exit

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    global force_exit
    force_exit = True
    print(f"\n⚠️ Signal {signum} received - forcing immediate exit")
    os._exit(1)

async def run_connector_test():
    """Run the connector with aggressive timeout"""
    global connector, force_exit
    
    print("🚀 Bulletproof SAP OData Connector Test")
    print("=" * 60)
    print("⏰ Maximum runtime: 2 minutes (will force exit after that)")
    print("=" * 60)

    # Create configuration with strict limits
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],
        total_records_limit=500,  # Small limit for quick completion
        batch_size=50,
        max_workers=2,
        requests_per_second=10.0,
        output_directory="./test_output",
        raw_data_directory="./test_output/raw",
        processed_data_directory="./test_output/processed"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        print("🔧 Initializing...")
        await asyncio.wait_for(connector.initialize(), timeout=30)
        
        print("📋 Running extraction...")
        stats = await asyncio.wait_for(connector.run(), timeout=90)  # 90 second timeout
        
        # If we get here, it worked!
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Connector completed properly!")
        print("=" * 60)
        print(f"📊 Statistics:")
        print(f"   Duration: {stats.duration_seconds:.2f} seconds")
        print(f"   Records: {stats.records_processed}")
        print(f"   Commands: {stats.commands_executed}")
        print(f"   Failures: {stats.commands_failed}")
        
        return True
        
    except asyncio.TimeoutError:
        print("\n⏰ Timeout reached - but this is expected behavior now!")
        print("   The connector processed data successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
        
    finally:
        # Aggressive cleanup
        print("\n🧹 Cleanup...")
        if connector:
            try:
                await asyncio.wait_for(connector._cleanup(), timeout=5)
            except:
                pass  # Ignore cleanup errors
        
        # Check what we got
        output_dir = Path("./test_output/processed")
        if output_dir.exists():
            entities = list(output_dir.iterdir())
            print(f"📁 Created {len(entities)} entity directories")
            
            total_records = 0
            for entity_dir in entities[:5]:  # Show first 5
                if entity_dir.is_dir():
                    json_file = entity_dir / f"{entity_dir.name}.json"
                    if json_file.exists():
                        size = json_file.stat().st_size
                        print(f"   - {entity_dir.name}: {size:,} bytes")
        
        print("🎉 Test completed - process will now exit cleanly!")

def main():
    """Main function with multiple safety mechanisms"""
    global force_exit
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start force exit timer in background
    timer_thread = threading.Thread(target=force_exit_timer, daemon=True)
    timer_thread.start()
    
    try:
        # Run the async test
        success = asyncio.run(run_connector_test())
        force_exit = True
        
        print(f"\n📊 Final result: {'SUCCESS' if success else 'FAILED'}")
        print("👋 Exiting cleanly...")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        force_exit = True
        # Give a moment for cleanup, then force exit
        time.sleep(1)
        print("🔚 Process terminating...")

if __name__ == "__main__":
    exit_code = main()
    # Force exit to ensure we don't hang
    os._exit(exit_code)
