"""
Test Automatic Saving Feature
==============================
This tests that the connector automatically saves query results to individual files.
"""

import asyncio
from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector


async def test_auto_save():
    """Test automatic saving of query results"""
    
    print("Testing Automatic Query Result Saving")
    print("=" * 50)
    
    # Configure connector
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./auto_save_test"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        # Initialize
        await connector.initialize()
        print("Connector initialized!")
        
        # Test 1: Basic query (should auto-save)
        print("\nTest 1: Basic Products Query")
        products = await connector.get_data(entity_name="Products")
        print(f"Retrieved {products['execution_stats']['records_processed']} products")
        
        # Test 2: Filtered query (should auto-save with filter info)
        print("\nTest 2: Filtered Products Query")
        expensive = await connector.get_data(
            entity_name="Products",
            filter_condition="UnitPrice gt 20"
        )
        print(f"Retrieved {expensive['execution_stats']['records_processed']} expensive products")
        
        # Test 3: Query with sorting (should auto-save with order info)
        print("\nTest 3: Sorted Products Query")
        sorted_products = await connector.get_data(
            entity_name="Products",
            order_by="UnitPrice desc"
        )
        print(f"Retrieved {sorted_products['execution_stats']['records_processed']} sorted products")
        
        # Test 4: Query with field selection (should auto-save with select info)
        print("\nTest 4: Selected Fields Query")
        selected = await connector.get_data(
            entity_name="Customers",
            select_fields="CustomerID,CompanyName,Country",
            filter_condition="Country eq 'Germany'"
        )
        print(f"Retrieved {selected['execution_stats']['records_processed']} German customers")
        
        print("\nAuto-save test completed!")
        print("Check ./auto_save_test/query_results/ for individual result files")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await connector.cleanup()


if __name__ == "__main__":
    asyncio.run(test_auto_save())
