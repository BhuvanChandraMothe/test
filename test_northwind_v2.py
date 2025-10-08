"""Test Northwind V2 service"""
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def test_northwind():
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc/",
        output_directory="./northwind_v2_test"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        print(f"\n✓ Entities found: {len(connector.metadata_service.schemas)}")
        print("\nEntity list:")
        for i, entity in enumerate(list(connector.metadata_service.schemas.keys())[:15], 1):
            print(f"  {i}. {entity}")
        
        print("\n" + "="*60)
        print("Fetching ALL entities...")
        print("="*60)
        
        result = await connector.get_data()
        
        print(f"\n✓ Total records: {result['execution_stats']['records_processed']}")
        print(f"  Duration: {result['execution_stats']['duration_seconds']:.2f} seconds")
        print(f"  Commands executed: {result['execution_stats']['commands_executed']}")
        
    finally:
        await connector.cleanup()

if __name__ == "__main__":
    asyncio.run(test_northwind())
