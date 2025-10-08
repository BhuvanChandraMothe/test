"""Test expand relations in filename"""
from covasant_odata.config.models import ClientConfig
from covasant_odata.connector import SAPODataConnector
import asyncio


async def test_multiple_expands():
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./expand_test"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        # Test 1: Single expand
        print("\n" + "="*60)
        print("Test 1: Single expand")
        print("="*60)
        result1 = await connector.get_data(
            entity_name="Products",
            expand_relations="Supplier",
            record_limit=5
        )
        print(f"✓ Fetched {result1['execution_stats']['records_processed']} records")
        
        # Test 2: Multiple expands
        print("\n" + "="*60)
        print("Test 2: Multiple expands")
        print("="*60)
        result2 = await connector.get_data(
            entity_name="Products",
            expand_relations="Supplier,Reviews",
            record_limit=5
        )
        print(f"✓ Fetched {result2['execution_stats']['records_processed']} records")
        
        # Test 3: No expand
        print("\n" + "="*60)
        print("Test 3: No expand")
        print("="*60)
        result3 = await connector.get_data(
            entity_name="Products",
            record_limit=5
        )
        print(f"✓ Fetched {result3['execution_stats']['records_processed']} records")
        
        # Test 4: Expand with filter
        print("\n" + "="*60)
        print("Test 4: Expand with filter")
        print("="*60)
        result4 = await connector.get_data(
            entity_name="Products",
            expand_relations="Supplier",
            filter_condition="Price gt 100",
            record_limit=5
        )
        print(f"✓ Fetched {result4['execution_stats']['records_processed']} records")
        
        print("\n" + "="*60)
        print("Check the files in ./expand_test/query_results/")
        print("="*60)
        
    finally:
        await connector.cleanup()


if __name__ == "__main__":
    asyncio.run(test_multiple_expands())
