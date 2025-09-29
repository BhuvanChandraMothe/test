#!/usr/bin/env python3
"""
Example demonstrating the new SAP OData Connector API with filtering capabilities
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig


async def demonstrate_filter_usage():
    """Demonstrate various filtering capabilities of the new API"""
    
    print("🔍 SAP OData Connector - Filter Usage Examples")
    print("=" * 60)
    
    # Configuration for Northwind test service
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,  # Public service
        password=None,
        total_records_limit=50,  # Keep it small for demo
        batch_size=10,
        max_workers=3,  # Used as cap, actual workers calculated automatically
        requests_per_second=3.0,
        output_directory="./filter_demo_output",
        raw_data_directory="./filter_demo_output/raw",
        processed_data_directory="./filter_demo_output/processed"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        # Step 1: Initialize and discover entities
        print("\n Step 1: Initializing connector...")
        entity_info = await connector.initialize()
        
        print(f"📊 Service discovered: {entity_info['total_entities']} entities available")
        print("Available entities:", [e['name'] for e in entity_info['entities'][:10]])
        
        # Step 2: Basic entity fetch (no filter)
        print("\n📦 Step 2: Fetch all Products (no filter)")
        result_all = await connector.get_data(
            entity_name="Products",
            record_limit=20
        )
        
        products_all = result_all['data'].get('Products', {}).get('records', [])
        print(f"✅ Fetched {len(products_all)} products")
        if products_all:
            print(f"   Sample: {products_all[0].get('ProductName')} - ${products_all[0].get('UnitPrice')}")
        
        # Step 3: Filter by price
        print("\n💰 Step 3: Filter Products with UnitPrice > 20")
        try:
            result_expensive = await connector.get_data(
                entity_name="Products",
                filter_condition="UnitPrice gt 20",
                record_limit=15
            )
            
            products_expensive = result_expensive['data'].get('Products', {}).get('records', [])
            print(f"✅ Fetched {len(products_expensive)} expensive products")
            if products_expensive:
                for product in products_expensive[:3]:
                    print(f"   - {product.get('ProductName')}: ${product.get('UnitPrice')}")
        
        except Exception as e:
            print(f"⚠️  Filter by price failed: {e}")
        
        # Step 4: Filter by category
        print("\n🏷️  Step 4: Filter Products by CategoryID")
        try:
            result_category = await connector.get_data(
                entity_name="Products",
                filter_condition="CategoryID eq 1",
                record_limit=10
            )
            
            products_category = result_category['data'].get('Products', {}).get('records', [])
            print(f"✅ Fetched {len(products_category)} products from category 1")
            if products_category:
                for product in products_category[:3]:
                    print(f"   - {product.get('ProductName')}")
        
        except Exception as e:
            print(f"⚠️  Filter by category failed: {e}")
        
        # Step 5: Complex filter
        print("\n🔍 Step 5: Complex filter - Products with price between 10 and 50")
        try:
            result_complex = await connector.get_data(
                entity_name="Products",
                filter_condition="UnitPrice ge 10 and UnitPrice le 50",
                record_limit=10
            )
            
            products_complex = result_complex['data'].get('Products', {}).get('records', [])
            print(f"✅ Fetched {len(products_complex)} products in price range $10-$50")
            if products_complex:
                for product in products_complex[:3]:
                    print(f"   - {product.get('ProductName')}: ${product.get('UnitPrice')}")
        
        except Exception as e:
            print(f"⚠️  Complex filter failed: {e}")
        
        # Step 6: Multiple entities with different filters
        print("\n🎯 Step 6: Fetch multiple entities separately")
        
        # Categories
        result_categories = await connector.get_data(
            entity_name="Categories",
            record_limit=5
        )
        categories = result_categories['data'].get('Categories', {}).get('records', [])
        print(f"✅ Fetched {len(categories)} categories")
        
        # Suppliers with filter
        try:
            result_suppliers = await connector.get_data(
                entity_name="Suppliers",
                filter_condition="Country eq 'USA'",
                record_limit=5
            )
            suppliers = result_suppliers['data'].get('Suppliers', {}).get('records', [])
            print(f"✅ Fetched {len(suppliers)} US suppliers")
        except Exception as e:
            print(f"⚠️  Supplier filter failed: {e}")
        
        # Step 7: Show execution statistics
        print("\n📈 Step 7: Execution Statistics Summary")
        print(f"   Total API calls made: {sum(r['execution_stats']['commands_executed'] for r in [result_all, result_expensive, result_category, result_complex, result_categories, result_suppliers] if 'execution_stats' in r)}")
        print(f"   Total records processed: {sum(r['execution_stats']['records_processed'] for r in [result_all, result_expensive, result_category, result_complex, result_categories, result_suppliers] if 'execution_stats' in r)}")
        print(f"   Dynamic workers used: {config.max_workers} (auto-calculated)")
        print(f"   Dynamic connections: {config.max_connections} (auto-calculated)")
        
        print("\n Filter demonstration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        if connector and hasattr(connector, 'proxy_pool') and connector.proxy_pool:
            try:
                await connector._cleanup()
            except:
                pass


async def demonstrate_api_comparison():
    """Compare old vs new API approaches"""
    
    print("\n" + "="*80)
    print("🔄 API COMPARISON: Old vs New Approach")
    print("="*80)
    
    print("\n📝 OLD API Pattern:")
    print("""
    # Old way - less flexible
    config = ClientConfig(
        selected_modules=["Products"],  # Had to specify upfront
        total_records_limit=100
    )
    connector = SAPODataConnector(config)
    await connector.initialize()  # No return value
    stats = await connector.run()  # No filtering, returns stats only
    
    # Had to manually check files for data
    # No immediate access to fetched data
    # Fixed connection pool settings
    """)
    
    print("\n✨ NEW API Pattern:")
    print("""
    # New way - much more flexible
    config = ClientConfig(...)  # Minimal config needed
    connector = SAPODataConnector(config)
    
    # Initialize returns entity information
    entities = await connector.initialize()
    print(f"Available: {entities['total_entities']} entities")
    
    # Flexible get_data with filtering
    result = await connector.get_data(
        entity_name="Products",
        filter_condition="UnitPrice gt 20",
        record_limit=50
    )
    
    # Immediate data access
    products = result['data']['Products']['records']
    stats = result['execution_stats']
    
    # Dynamic connection pool sizing
    # Structured result format
    # Built-in filtering support
    """)
    
    print("\n💡 Key Improvements:")
    print("   ✅ initialize() returns entity metadata")
    print("   ✅ run() supports entity-specific filtering")
    print("   ✅ Dynamic connection pool sizing")
    print("   ✅ Immediate data access in results")
    print("   ✅ Structured execution statistics")
    print("   ✅ Better error handling and logging")


if __name__ == "__main__":
    print("🚀 Starting SAP OData Connector Filter Usage Examples")
    
    # Run the demonstration
    success = asyncio.run(demonstrate_filter_usage())
    
    if success:
        # Show API comparison
        asyncio.run(demonstrate_api_comparison())
    
    print(f"\n🏁 Demo result: {'SUCCESS' if success else 'FAILED'}")
    
    # Clean exit
    import os
    os._exit(0 if success else 1)
