#!/usr/bin/env python3
"""Debug script to test the full execution flow"""

import asyncio
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent / "odc"))

from config.models import ClientConfig
from connector import SAPODataConnector

async def debug_execution():
    """Debug the full execution flow with detailed logging"""
    
    # Set up detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔍 Debugging full execution flow...")
    
    # Create test configuration with very small limits
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],  # All entities
        total_records_limit=10,  # Very small limit
        batch_size=5,
        max_workers=1,  # Single worker for easier debugging
        requests_per_second=0.5,  # Very slow to avoid rate limiting
        output_directory="./debug_output",
        raw_data_directory="./debug_output/raw",
        processed_data_directory="./debug_output/processed"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        print("🚀 Initializing connector...")
        await connector.initialize()
        print("✅ Initialization completed")
        
        print("\n📋 Starting discovery phase...")
        await connector._discovery_phase(None)
        print("✅ Discovery phase completed")
        
        # Check what was discovered
        if hasattr(connector, 'plan_generator') and connector.plan_generator:
            initial_commands = connector.plan_generator.get_initial_commands()
            print(f"📊 Initial commands generated: {len(initial_commands)}")
            for i, cmd in enumerate(initial_commands[:3]):  # Show first 3
                print(f"  Command {i+1}: {cmd}")
        
        print("\n🔧 Starting execution phase...")
        await connector._execution_phase()
        print("✅ Execution phase completed")
        
        print("\n📈 Final stats:")
        print(f"  Entities processed: {connector.stats.entities_processed}")
        print(f"  Records processed: {connector.stats.records_processed}")
        print(f"  Commands executed: {connector.stats.commands_executed}")
        print(f"  Commands failed: {connector.stats.commands_failed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if connector.proxy_pool:
            await connector.proxy_pool.stop()

if __name__ == "__main__":
    success = asyncio.run(debug_execution())
    sys.exit(0 if success else 1)
