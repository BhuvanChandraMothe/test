"""
Example showing the new SAP Connector API with service type selection
and runtime execution parameters
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.config.models import ClientConfig, ServiceType, ConnectorFactory


async def demonstrate_new_api():
    """Demonstrate the new simplified API structure"""
    
    print("🔄 New SAP Connector API - Service Type Selection")
    print("=" * 60)
    
    # STEP 1: Configuration with Module Selection
    print("\n📋 Step 1: Create configuration with module selection")
    config = ClientConfig(
        service_type=ServiceType.ODATA,  # Choose service type
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,  # No credentials needed for public service
        password=None,
        selected_modules=["Products", "Categories", "Suppliers"],  # Specific modules to process
        output_directory="./new_api_demo"
    )
    
    print(f"   ✅ Service Type: {config.service_type}")
    print(f"   ✅ Service URL: {config.service_url}")
    print(f"   ✅ Selected Modules: {', '.join(config.selected_modules)}")
    print(f"   ✅ Output Directory: {config.output_directory}")
    
    # STEP 2: Create Connector using Factory
    print("\n🏭 Step 2: Create connector using factory pattern")
    try:
        connector = ConnectorFactory.create_connector(config)
        print(f"   ✅ Created OData connector successfully")
    except NotImplementedError as e:
        print(f"   ⚠️  {e}")
        return False
    
    # STEP 3: Initialize
    print("\n🔧 Step 3: Initialize connector")
    try:
        entity_info = await connector.initialize()
        print(f"   ✅ Discovered {entity_info['total_entities']} entities")
        print(f"   ✅ Total records available: {entity_info['total_records']:,}")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False
    
    # STEP 4: Get Data with Runtime Parameters
    print("\n📊 Step 4: Get data with runtime execution parameters")
    
    # Scenario 1: Small batch, conservative settings
    print("\n   Scenario 1: Conservative settings for small dataset")
    result1 = await connector.get_data(
        entity_name="Categories",
        record_limit=10,
        batch_size=5,           # Small batches
        max_workers=2,          # Few workers
        requests_per_second=2.0 # Slow rate
    )
    
    categories = result1['data'].get('Categories', {})
    print(f"   ✅ Fetched {categories.get('count', 0)} categories")
    print(f"   ⏱️  Duration: {result1['execution_stats']['duration_seconds']:.2f}s")
    
    # Scenario 2: Larger batch, aggressive settings
    print("\n   Scenario 2: Aggressive settings for larger dataset")
    result2 = await connector.get_data(
        entity_name="Products",
        record_limit=50,
        batch_size=25,          # Larger batches
        max_workers=5,          # More workers
        requests_per_second=10.0 # Faster rate
    )
    
    products = result2['data'].get('Products', {})
    print(f"   ✅ Fetched {products.get('count', 0)} products")
    print(f"   ⏱️  Duration: {result2['execution_stats']['duration_seconds']:.2f}s")
    
    # Scenario 3: Filtered query with custom settings
    print("\n   Scenario 3: Filtered query with custom settings")
    try:
        result3 = await connector.get_data(
            entity_name="Products",
            filter_condition="UnitPrice gt 20",
            record_limit=20,
            batch_size=10,
            max_workers=3,
            requests_per_second=5.0
        )
        
        filtered_products = result3['data'].get('Products', {})
        print(f"   ✅ Fetched {filtered_products.get('count', 0)} expensive products")
        print(f"   ⏱️  Duration: {result3['execution_stats']['duration_seconds']:.2f}s")
        
        # Show sample data
        if filtered_products.get('records'):
            sample = filtered_products['records'][0]
            print(f"   📋 Sample: {sample.get('ProductName')} - ${sample.get('UnitPrice')}")
            
    except Exception as e:
        print(f"   ⚠️  Filter query failed: {e}")
    
    print("\n🎉 New API demonstration completed!")
    
    return True


async def demonstrate_future_service_types():
    """Show how other service types would work in the future"""
    
    print("\n🔮 Future Service Types (Work in Progress)")
    print("=" * 60)
    
    # REST Example (Future)
    print("\n🌐 REST Service Example (Work in Progress):")
    print("""
    config = ClientConfig(
        service_type=ServiceType.REST,
        service_url="https://api.sap.com/v1",
        username="your_username",
        password="your_password",
        client_id="your_client_id",
        client_secret="your_client_secret",
        selected_modules=["customers", "orders", "products"]
    )
    
    connector = ConnectorFactory.create_connector(config)
    result = await connector.get_data(
        endpoint="/customers",
        method="GET",
        headers={"Accept": "application/json"},
        batch_size=100
    )
    """)
    
    # STREAMING Example (Future)
    print("\n📡 Streaming Service Example (Work in Progress):")
    print("""
    config = ClientConfig(
        service_type=ServiceType.STREAMING,
        service_url="wss://streaming.sap.com/events",
        username="your_username",
        password="your_password",
        selected_modules=["real_time_orders", "inventory_updates", "alerts"]
    )
    
    connector = ConnectorFactory.create_connector(config)
    
    # Stream data continuously
    async for batch in connector.get_data_stream(
        stream_name="real_time_orders",
        batch_size=50,
        timeout_seconds=30
    ):
        process_streaming_data(batch)
    
    # Or get batch of streaming data
    result = await connector.get_data(
        stream_name="inventory_updates",
        max_records=1000,
        timeout_seconds=60
    )
    """)


if __name__ == "__main__":
    print("🚀 Starting New SAP Connector API Demonstration")
    
    # Run the demonstration
    success = asyncio.run(demonstrate_new_api())
    
    if success:
        # Show future possibilities
        asyncio.run(demonstrate_future_service_types())
    
    print(f"\n🏁 Demo result: {'SUCCESS' if success else 'FAILED'}")
    
    # Clean exit
    import os
    os._exit(0 if success else 1)
