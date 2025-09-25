#!/usr/bin/env python3
"""
Test script to check foreign key relationship parsing
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def test_relationships():
    """Test relationship parsing"""
    print("🔍 Testing Foreign Key Relationship Parsing")
    print("=" * 60)
    
    # Create configuration
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],
        total_records_limit=10,  # Very small limit for quick test
        batch_size=5,
        max_workers=1,
        requests_per_second=10.0,
        output_directory="./test_output",
        raw_data_directory="./test_output/raw",
        processed_data_directory="./test_output/processed"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        print("🔧 Initializing connector...")
        await connector.initialize()
        
        print("📋 Checking metadata and relationships...")
        
        # Get the metadata service to check relationships
        metadata_service = connector.metadata_service
        relationships = metadata_service.get_foreign_key_relationships()
        
        print(f"\n📊 Relationship Analysis:")
        print(f"   Total entities: {len(metadata_service.schemas)}")
        print(f"   Entities with relationships: {len(relationships)}")
        
        if relationships:
            print(f"\n🔗 Foreign Key Relationships Found:")
            for entity_name, entity_relationships in relationships.items():
                print(f"\n   📋 {entity_name}:")
                for rel in entity_relationships:
                    print(f"      - {rel['from_property']} -> {rel['to_entity']}.{rel['to_property']}")
        else:
            print(f"\n⚠️ No foreign key relationships found!")
            print(f"   This might indicate a parsing issue.")
        
        # Check navigation properties
        print(f"\n🧭 Navigation Properties:")
        nav_count = 0
        for entity_name, schema in metadata_service.schemas.items():
            if schema.navigation_properties:
                nav_count += len(schema.navigation_properties)
                print(f"   📋 {entity_name}:")
                for nav_name, nav_info in schema.navigation_properties.items():
                    print(f"      - {nav_name} -> {nav_info['target_entity']}")
        
        print(f"\n   Total navigation properties: {nav_count}")
        
        # Save updated entity relationships file
        er_file = await metadata_service.save_entity_relationship_file("./test_output")
        print(f"\n📄 Updated entity relationships file: {er_file}")
        
        # Check the file content
        with open(er_file, 'r') as f:
            er_data = json.load(f)
        
        print(f"\n📈 File Summary:")
        print(f"   Entities: {er_data['summary']['entity_count']}")
        print(f"   Relationships: {er_data['summary']['relationship_count']}")
        
        if er_data['summary']['relationship_count'] > 0:
            print(f"\n✅ SUCCESS: Foreign key relationships are now being parsed!")
        else:
            print(f"\n❌ ISSUE: Still no relationships found. Need to investigate further.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    try:
        success = asyncio.run(test_relationships())
        print(f"\n📊 Test result: {'SUCCESS' if success else 'FAILED'}")
        
        # Immediate exit
        os._exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        os._exit(1)

if __name__ == "__main__":
    main()
