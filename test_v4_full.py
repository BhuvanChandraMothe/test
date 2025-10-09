"""Full V4 test - get ALL records"""
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def test_v4_full():
    print("\n" + "="*70)
    print("FULL V4 TEST - Fetching ALL records")
    print("="*70)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc/",
        output_directory="./test_v4_full",
        timeout=500
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        await connector.get_data(entity_name="Alphabetical_list_of_products", group_by="CategoryID")
    finally:
        await connector.cleanup()

if __name__ == "__main__":
    success = asyncio.run(test_v4_full())
