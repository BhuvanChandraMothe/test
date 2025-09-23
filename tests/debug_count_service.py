#!/usr/bin/env python3
"""Debug script to test count service and execution flow"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent / "odc"))

from config.models import ClientConfig, ODataConfig
from services.metadata import MetadataService
from services.count import CountService

async def debug_count_service():
    """Debug count service and execution flow"""
    
    print("🔍 Debugging count service...")
    
    # Create config
    odata_config = ODataConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc"
    )
    
    try:
        # Test metadata service first
        print("📋 Testing metadata service...")
        async with MetadataService(odata_config) as metadata_service:
            schemas = await metadata_service.fetch_metadata()
            print(f"Found {len(schemas)} entity schemas")
            
            entity_names = list(schemas.keys())[:5]  # Test first 5 entities
            print(f"Testing entities: {entity_names}")
        
        # Test count service
        print("\n📊 Testing count service...")
        async with CountService(odata_config) as count_service:
            entity_counts = await count_service.get_entity_counts(entity_names)
            print(f"Entity counts: {entity_counts}")
            
            # Test individual entity count
            if entity_names:
                first_entity = entity_names[0]
                print(f"\n🔍 Testing individual count for {first_entity}...")
                try:
                    count = await count_service._get_single_entity_count(first_entity)
                    print(f"Count for {first_entity}: {count}")
                except Exception as e:
                    print(f"Error getting count for {first_entity}: {e}")
                    
                # Test sample data
                print(f"\n📄 Testing sample data for {first_entity}...")
                try:
                    sample = await count_service.get_entity_sample(first_entity, 2)
                    print(f"Sample data ({len(sample)} records): {sample}")
                except Exception as e:
                    print(f"Error getting sample for {first_entity}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_count_service())
    sys.exit(0 if success else 1)
