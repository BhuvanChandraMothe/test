from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def test():
    c = SAPODataConnector(ClientConfig(
        service_url='https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/',
        username='P2010682507',
        password='Bhuvan@2001',
        output_directory='./quick_test'
    ))
    await c.initialize()
    r = await c.get_data(entity_name='Products')
    print(f'✅ V2 Test: {r["execution_stats"]["records_processed"]}/5 records - WORKING!')
    await c.cleanup()

asyncio.run(test())
