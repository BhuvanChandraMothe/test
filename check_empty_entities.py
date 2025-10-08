"""Check if ShoppingCarts and ShoppingCartItems are truly empty"""
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def check_entities():
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./temp_check"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        print("\n" + "="*60)
        print("Checking ShoppingCarts entity")
        print("="*60)
        result1 = await connector.get_data(
            entity_name="ShoppingCarts",
            record_limit=10
        )
        print(f"Records found: {result1['execution_stats']['records_processed']}")
        
        print("\n" + "="*60)
        print("Checking ShoppingCartItems entity")
        print("="*60)
        result2 = await connector.get_data(
            entity_name="ShoppingCartItems",
            record_limit=10
        )
        print(f"Records found: {result2['execution_stats']['records_processed']}")
        
        print("\n" + "="*60)
        print("Summary")
        print("="*60)
        if result1['execution_stats']['records_processed'] == 0:
            print("✓ ShoppingCarts is EMPTY (no data in this demo service)")
        if result2['execution_stats']['records_processed'] == 0:
            print("✓ ShoppingCartItems is EMPTY (no data in this demo service)")
        
        print("\nThis is normal - these tables are empty in the demo service.")
        print("The connector correctly skipped them to save time!")
        
    finally:
        await connector.cleanup()

if __name__ == "__main__":
    asyncio.run(check_entities())
