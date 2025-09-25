#!/usr/bin/env python3
"""
Debug script to examine raw metadata and find relationship patterns
"""

import asyncio
import httpx
import xml.etree.ElementTree as ET
import os
import sys

async def debug_metadata():
    """Debug the raw metadata to understand relationship structure"""
    print("🔍 Debugging Northwind Metadata for Relationships")
    print("=" * 60)
    
    # Fetch raw metadata
    url = "https://services.odata.org/V4/Northwind/Northwind.svc/$metadata"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        
        metadata_xml = response.text
        
        # Save raw metadata for inspection
        with open("./test_output/raw_metadata.xml", "w", encoding="utf-8") as f:
            f.write(metadata_xml)
        
        print(f"📄 Raw metadata saved to: ./test_output/raw_metadata.xml")
        print(f"📊 Metadata size: {len(metadata_xml):,} characters")
        
        # Parse and analyze
        root = ET.fromstring(metadata_xml)
        
        # Define namespaces
        namespaces = {
            'edmx': 'http://docs.oasis-open.org/odata/ns/edmx',
            'edm': 'http://docs.oasis-open.org/odata/ns/edm'
        }
        
        print(f"\n🔍 Analyzing metadata structure...")
        
        # Check for navigation properties
        nav_props = root.findall('.//edm:NavigationProperty', namespaces)
        print(f"📋 Navigation Properties found: {len(nav_props)}")
        
        if nav_props:
            print(f"\n🧭 Sample Navigation Properties:")
            for i, nav_prop in enumerate(nav_props[:5]):  # Show first 5
                name = nav_prop.get('Name')
                nav_type = nav_prop.get('Type')
                partner = nav_prop.get('Partner')
                
                print(f"   {i+1}. {name}:")
                print(f"      Type: {nav_type}")
                print(f"      Partner: {partner}")
                
                # Check for referential constraints
                ref_constraint = nav_prop.find('edm:ReferentialConstraint', namespaces)
                if ref_constraint is not None:
                    prop = ref_constraint.get('Property')
                    ref_prop = ref_constraint.get('ReferencedProperty')
                    print(f"      🔗 FK: {prop} -> {ref_prop}")
                else:
                    print(f"      ❌ No referential constraint")
        
        # Check for associations (legacy)
        associations = root.findall('.//edm:Association', namespaces)
        print(f"\n📋 Associations found: {len(associations)}")
        
        # Check for entity types with foreign key properties
        entity_types = root.findall('.//edm:EntityType', namespaces)
        print(f"\n📋 Entity Types found: {len(entity_types)}")
        
        # Look for properties that might be foreign keys (end with ID)
        fk_candidates = []
        for entity_type in entity_types:
            entity_name = entity_type.get('Name')
            properties = entity_type.findall('edm:Property', namespaces)
            
            for prop in properties:
                prop_name = prop.get('Name')
                prop_type = prop.get('Type')
                
                # Look for properties that end with ID and are not the primary key
                if prop_name and prop_name.endswith('ID') and prop_name != f"{entity_name}ID":
                    fk_candidates.append({
                        'entity': entity_name,
                        'property': prop_name,
                        'type': prop_type
                    })
        
        print(f"\n🔍 Potential Foreign Key Properties (ending with 'ID'):")
        for fk in fk_candidates[:10]:  # Show first 10
            print(f"   - {fk['entity']}.{fk['property']} ({fk['type']})")
        
        if len(fk_candidates) > 10:
            print(f"   ... and {len(fk_candidates) - 10} more")
        
        # Check specific entities that should have relationships
        print(f"\n🔍 Checking specific entities for relationships:")
        
        # Products should reference Categories
        products_entity = None
        for entity_type in entity_types:
            if entity_type.get('Name') == 'Product':
                products_entity = entity_type
                break
        
        if products_entity is not None:
            print(f"\n📋 Product entity analysis:")
            properties = products_entity.findall('edm:Property', namespaces)
            nav_properties = products_entity.findall('edm:NavigationProperty', namespaces)
            
            print(f"   Properties: {[p.get('Name') for p in properties]}")
            print(f"   Navigation Properties: {[p.get('Name') for p in nav_properties]}")
            
            # Check for CategoryID property
            category_id_prop = None
            for prop in properties:
                if prop.get('Name') == 'CategoryID':
                    category_id_prop = prop
                    break
            
            if category_id_prop is not None:
                print(f"   ✅ Found CategoryID property: {category_id_prop.get('Type')}")
            else:
                print(f"   ❌ No CategoryID property found")
            
            # Check navigation properties for Category reference
            for nav_prop in nav_properties:
                name = nav_prop.get('Name')
                nav_type = nav_prop.get('Type')
                if 'Category' in nav_type:
                    print(f"   ✅ Found Category navigation: {name} -> {nav_type}")
                    
                    # Check for referential constraint
                    ref_constraint = nav_prop.find('edm:ReferentialConstraint', namespaces)
                    if ref_constraint is not None:
                        prop = ref_constraint.get('Property')
                        ref_prop = ref_constraint.get('ReferencedProperty')
                        print(f"      🔗 Referential Constraint: {prop} -> {ref_prop}")
                    else:
                        print(f"      ❌ No referential constraint on this navigation property")

def main():
    """Main function"""
    try:
        asyncio.run(debug_metadata())
        print(f"\n✅ Metadata analysis completed!")
        print(f"💡 Check the raw_metadata.xml file for detailed inspection")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
