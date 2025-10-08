"""Check actual field names in Products entity"""
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def check_fields():
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./temp"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        # Get just 1 product to see field names
        result = await connector.get_data(
            entity_name="Products",
            record_limit=1
        )
        
        if result['records']:
            first_product = result['records'][0]
            print("\n" + "="*60)
            print("Available field names in Products entity:")
            print("="*60)
            for key in sorted(first_product.keys()):
                if not key.startswith('__'):
                    print(f"  - {key}")
            
            print("\n" + "="*60)
            print("Sample product data:")
            print("="*60)
            for key, value in first_product.items():
                if not key.startswith('__') and not key.startswith('@'):
                    print(f"  {key}: {value}")
        
    finally:
        await connector.cleanup()

if __name__ == "__main__":
    asyncio.run(check_fields())
