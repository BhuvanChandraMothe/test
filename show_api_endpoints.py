#!/usr/bin/env python3
"""
Show all API endpoints that will be accessed without running the full extraction
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def show_endpoints():
    """Show all API endpoints that will be accessed"""
    print("🌐 SAP OData Connector - API Endpoint Preview")
    print("=" * 60)
    
    # Create configuration
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],  # All entities
        total_records_limit=500,  # Example limit
        batch_size=50,
        max_workers=2,
        requests_per_second=10.0,
        output_directory="./test_output",
        raw_data_directory="./test_output/raw",
        processed_data_directory="./test_output/processed"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        print("🔧 Initializing connector to discover endpoints...")
        await connector.initialize()
        
        print("\n📋 Starting discovery to show all API endpoints...")
        
        # Run only the discovery phase to show endpoints
        await connector._discovery_phase(None)
        
        print("\n✅ Endpoint discovery completed!")
        print("💡 This shows all the API calls that would be made during full execution.")
        print("🚀 To run the actual extraction, use: python test_direct_exit.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during endpoint discovery: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    try:
        success = asyncio.run(show_endpoints())
        print(f"\n📊 Endpoint discovery: {'SUCCESS' if success else 'FAILED'}")
        
        # Immediate exit
        os._exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        os._exit(1)

if __name__ == "__main__":
    main()
