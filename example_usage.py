"""
Example: Using SAP OData Connector as an installed package
This file demonstrates how to use the connector from anywhere after installation
"""

import asyncio
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig


async def main():
    """
    Example usage of SAP OData Connector
    After running 'pip install -e .' you can use this code anywhere!
    """
    
    print("=" * 60)
    print("SAP OData Connector - Example Usage")
    print("=" * 60)
    
    # Configure the connector
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./example_output"
    )
    
    # Create connector instance
    connector = SAPODataConnector(config)
    
    try:
        # Initialize
        await connector.initialize()
        print("\n✅ Connector initialized successfully!")
        
        # Example 1: Simple query
        print("\n📊 Example 1: Fetching all Products...")
        products = await connector.get_data(entity_name="Products")
        print(f"   Retrieved {products['execution_stats']['records_processed']} products")
        
        # Example 2: Query with expansion (JOIN)
        print("\n📊 Example 2: Fetching Products with Supplier data...")
        products_with_suppliers = await connector.get_data(
            entity_name="Products",
            expand_relations="Supplier"
        )
        print(f"   Retrieved {products_with_suppliers['execution_stats']['records_processed']} products with supplier info")
        
        # Example 3: Filtered query
        print("\n📊 Example 3: Fetching Reviews...")
        reviews = await connector.get_data(
            entity_name="Reviews",
            select_fields="Id,Rating,Comment,ProductId",
            order_by="Rating desc"
        )
        print(f"   Retrieved {reviews['execution_stats']['records_processed']} reviews")
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print(f"📁 Results saved to: {config.output_directory}/query_results/")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    
    finally:
        await connector.cleanup()
        print("\n🧹 Cleanup completed")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
