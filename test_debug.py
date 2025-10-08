import asyncio
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig

async def debug_test():
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./demo_output_debug"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        print("\n" + "="*80)
        print("INITIALIZING CONNECTOR")
        print("="*80)
        await connector.initialize()
        
        print("\n" + "="*80)
        print("STARTING DATA FETCH")
        print("="*80)
        
        # Use simple query first to verify it works
        print("\nTest 1: Simple query (entity_name)")
        result1 = await connector.get_data(
            entity_name="Reviews",
            batch_size=500,
            record_limit=100  # Limit to 100 for quick test
        )
        
        print(f"\n✓ Simple query completed:")
        print(f"  Records: {result1['execution_stats']['records_processed']}")
        print(f"  Duration: {result1['execution_stats']['duration_seconds']:.2f}s")
        print(f"  Pages: {result1['execution_stats'].get('pages_fetched', 'N/A')}")
        
    finally:
        await connector.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_test())
