import asyncio
import os
import shutil
import sys

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig
from odc.monitoring.metrics import get_metrics_collector
from prometheus_client import push_to_gateway



PUSH_GATEWAY_URL = 'http://localhost:9091'

PROMETHEUS_JOB_NAME = 'sap_odata_connector'

async def test_northwind():
    """Test the connector with new API structure"""
    
    
    print("=" * 50)
    
    
    metrics_collector = get_metrics_collector()

    # Clean up output directory from previous runs
    output_dir = "./test_output"
    if os.path.exists(output_dir):
        print(f"Cleaning up previous test output: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create configuration for SAP OData service
    config = ClientConfig(
        service_type="odata",  # Specify service type
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,  # No auth needed for public service
        password=None,
        # service_url="https://your-sap-server:port/sap/opu/odata/sap/SERVICE_NAME/",
        # username="your_sap_username",
        # password="your_sap_password", 
        # sap_client="100",  # SAP client number
        # system_id="PRD",   # SAP system ID
        selected_modules=[],  # Specific entities to process
        output_directory="./test_output"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        #init
        print("\n STEP 1: Initializing connector and discovering entities...")
        await connector.initialize()
    
        
        # Get data with execution parameters (no longer in config)
        # await connector.get_data(
        #     record_limit=100,
        #     batch_size=50,
        #     max_workers=5,
        #     requests_per_second=5.0
        # )
       
        
        # #specific dhanlo thevadaniki
        await connector.get_data(entity_name="Invoices", record_limit=20)
        
        
        # #filter cheydaniki
        # await connector.get_data(
        #         entity_name="Invoices", 
        #         filter_condition="UnitPrice gt 100",
        #         record_limit=10
        #     )
        
        
        #edhi grafana kosam
        try:
            push_to_gateway(
                PUSH_GATEWAY_URL,
                job=PROMETHEUS_JOB_NAME,
                registry=metrics_collector.registry
            )
            print("    Metrics pushed successfully!")
        except Exception as e:
            print(f"   Failed to push metrics: {e}")
        
        
        
        return True
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Ensure cleanup
        if connector and connector.proxy_pool:
            try:
                await connector._cleanup()
            except:
                pass




if __name__ == "__main__":
    print("\nRunning SAP OData Connector Test...")
    success = asyncio.run(test_northwind())
    
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
    
    # Force exit to ensure no hanging
    import os
    os._exit(0 if success else 1)