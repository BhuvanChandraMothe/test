#!/usr/bin/env python3
"""Debug script to test metadata parsing"""

import asyncio
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent / "odc"))

from config.models import ODataConfig
from services.metadata import MetadataService

async def debug_metadata():
    """Debug metadata parsing"""
    
    print("🔍 Debugging metadata parsing...")
    
    # Create config
    config = ODataConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc"
    )
    
    # Create metadata service
    metadata_service = MetadataService(config)
    
    try:
        async with metadata_service:
            # First, let's see what the raw metadata looks like
            print("📋 Fetching raw metadata...")
            response = await metadata_service._client.get(config.metadata_url)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                edmx_content = response.text
                print(f"Content length: {len(edmx_content)}")
                
                # Parse XML to see structure
                root = ET.fromstring(edmx_content)
                print(f"Root tag: {root.tag}")
                print(f"Root attributes: {root.attrib}")
                
                # Check namespaces
                print("\n🏷️ Namespaces found:")
                for prefix, uri in root.attrib.items():
                    if prefix.startswith('xmlns'):
                        print(f"  {prefix}: {uri}")
                
                # Look for entity types with different namespace patterns
                print("\n📊 Looking for EntityTypes...")
                
                # Try different namespace combinations
                namespace_patterns = [
                    {'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx', 'edm': 'http://schemas.microsoft.com/ado/2008/09/edm'},
                    {'edmx': 'http://docs.oasis-open.org/odata/ns/edmx', 'edm': 'http://docs.oasis-open.org/odata/ns/edm'},
                    {},  # No namespaces
                ]
                
                for i, ns in enumerate(namespace_patterns):
                    print(f"\nTrying namespace pattern {i+1}: {ns}")
                    if ns:
                        entity_types = root.findall('.//edm:EntityType', ns)
                        entity_sets = root.findall('.//edm:EntitySet', ns)
                    else:
                        # Try without namespaces
                        entity_types = root.findall('.//EntityType')
                        entity_sets = root.findall('.//EntitySet')
                    
                    print(f"  Found {len(entity_types)} EntityTypes")
                    print(f"  Found {len(entity_sets)} EntitySets")
                    
                    if entity_types:
                        for et in entity_types[:3]:  # Show first 3
                            print(f"    EntityType: {et.get('Name')}")
                    
                    if entity_sets:
                        for es in entity_sets[:3]:  # Show first 3
                            print(f"    EntitySet: {es.get('Name')} -> {es.get('EntityType')}")
                
                # Now try the actual metadata service
                print("\n🔧 Testing MetadataService.fetch_metadata()...")
                schemas = await metadata_service.fetch_metadata()
                print(f"Schemas found: {len(schemas)}")
                for name, schema in list(schemas.items())[:5]:  # Show first 5
                    print(f"  {name}: {len(schema.properties)} properties, keys: {schema.keys}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_metadata())
    sys.exit(0 if success else 1)
