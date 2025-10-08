from covasant_odata.config.models import ClientConfig
from covasant_odata.connector import SAPODataConnector
import asyncio


async def main():
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./join_demo"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        result = await connector.get_data(
            entity_name="Products",
            expand_relations="Supplier",
            batch_size=300,
            
        )
        
        print(f"\n✓ Fetched {result['execution_stats']['records_processed']} records")
        print(f"  Duration: {result['execution_stats']['duration_seconds']:.2f} seconds")
        
        # The data is saved to query_results folder - let's check that
        print(f"\n📁 Data saved to: ./test_joins_output/query_results/")
        print(f"   Check the JSON file to see expanded Supplier data!")
        
        # Also check if raw records are in result
        if 'records' in result:
            print(f"\n✓ Found {len(result['records'])} records in result")
            if result['records']:
                first_record = result['records'][0]
                if 'Supplier' in first_record:
                    supplier = first_record['Supplier']
                    if isinstance(supplier, dict) and 'CompanyName' in supplier:
                        print(f"\n✅ EXPAND WORKING! First product's supplier:")
                        print(f"   Company: {supplier.get('CompanyName')}")
                        print(f"   Contact: {supplier.get('ContactName')}")
                        print(f"   City: {supplier.get('City')}")
                    else:
                        print(f"\n⚠️  Supplier is present but might be deferred: {supplier}")
                else:
                    print(f"\n⚠️  No Supplier key found. Available keys: {list(first_record.keys())[:10]}")
        
        return result
        
    finally:
        await connector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
