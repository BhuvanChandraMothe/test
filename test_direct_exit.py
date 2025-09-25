#!/usr/bin/env python3
"""
Direct exit test - no hanging, immediate termination
"""

import asyncio
import os
import sys
import signal
from pathlib import Path

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

def signal_handler(signum, frame):
    """Immediate exit on signal"""
    print(f"\n⚠️ Signal {signum} - exiting immediately")
    os._exit(1)

async def run_test():
    """Run test with immediate exit"""
    print("🚀 Direct Exit Test - SAP OData Connector")
    print("=" * 50)
    
    # Simple config
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],
        total_records_limit=300,  # Small limit
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
        await connector.initialize()
        
        print("📋 Running extraction...")
        stats = await connector.run()
        
        # Show stats immediately
        print("\n✅ COMPLETED!")
        print(f"Duration: {stats.duration_seconds:.1f}s")
        print(f"Records: {stats.records_processed}")
        print(f"Commands: {stats.commands_executed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # NO finally block - no cleanup to avoid hanging

def main():
    """Main with immediate exit"""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = asyncio.run(run_test())
        
        # Show final result
        print(f"\n📊 Result: {'SUCCESS' if success else 'FAILED'}")
        
        # Check output quickly
        output_dir = Path("./test_output/processed")
        if output_dir.exists():
            entities = len(list(output_dir.iterdir()))
            print(f"📁 Created {entities} entity files")
        
        print("👋 Exiting now...")
        
        # IMMEDIATE EXIT - no cleanup, no waiting
        os._exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        os._exit(1)

if __name__ == "__main__":
    main()
