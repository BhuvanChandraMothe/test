from covasant_odata.config.models import ClientConfig
from covasant_odata.connector import SAPODataConnector
import asyncio


async def main():
    config = ClientConfig(
        # service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        # username="P2010682507",
        # password="Bhuvan@2001",
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        sap_module="ES5",  
        use_https=True,
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./demo_output_batch"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        # cat = await connector.get_data(
        #     entity_name="Products",
        #     expand_relations="Suppliers",
        #     batch_size=300,
            
        # )
        
        # bat = await connector.get_data(
        #     entity_name="Images",
        #     batch_size=50
        # )
        
        # print(f"\n[SUCCESS] Fetched {cat['execution_stats']['records_processed']} records")
        # print(f"  Duration: {cat['execution_stats']['duration_seconds']:.2f} seconds")
        # print(f"  Entities processed: {cat['execution_stats']['entities_processed']}")
        # print(f"  Commands executed: {cat['execution_stats']['commands_executed']}")
        
        
        result = await connector.get_data()
        
        print(f"\n[SUCCESS] Fetched {result['execution_stats']['records_processed']} records")
        print(f"  Duration: {result['execution_stats']['duration_seconds']:.2f} seconds")
        # Note: 'pages_fetched' only exists for simple queries (entity_name)
        # For full pipeline (selected_entities), use 'commands_executed' instead
        
    finally:
        # Properly cleanup the session
        await connector.cleanup()

asyncio.run(main())