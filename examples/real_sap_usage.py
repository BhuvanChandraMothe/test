"""
Example for connecting to real SAP systems with proper authentication
and module selection
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.config.models import ClientConfig, ServiceType
from odc.connector import SAPODataConnector


async def connect_to_real_sap():
    """Example of connecting to a real SAP system"""
    
    print("🏢 Real SAP System Connection Example")
    print("=" * 50)
    
    # EXAMPLE 1: SAP S/4HANA OData Service
    print("\n📊 Example 1: SAP S/4HANA Business Partner Service")
    s4hana_config = ClientConfig(
        service_type=ServiceType.ODATA,
        service_url="https://your-s4hana-server:44300/sap/opu/odata/sap/API_BUSINESS_PARTNER/",
        username="your_sap_username",
        password="your_sap_password",
        sap_client="100",  # SAP client number
        system_id="S4H",   # SAP system ID
        selected_modules=[
            "A_BusinessPartner",
            "A_Customer", 
            "A_Supplier",
            "A_BusinessPartnerAddress"
        ],
        output_directory="./sap_s4hana_data"
    )
    
    print(f"   🔗 Service URL: {s4hana_config.service_url}")
    print(f"   👤 SAP Client: {s4hana_config.sap_client}")
    print(f"   🏷️  System ID: {s4hana_config.system_id}")
    print(f"   📦 Modules: {', '.join(s4hana_config.selected_modules)}")
    
    # EXAMPLE 2: SAP SuccessFactors OData Service
    print("\n👥 Example 2: SAP SuccessFactors Employee Central")
    successfactors_config = ClientConfig(
        service_type=ServiceType.ODATA,
        service_url="https://api4.successfactors.com/odata/v2/",
        username="your_sf_username",
        password="your_sf_password",
        # SuccessFactors uses OAuth, so you might use:
        client_id="your_oauth_client_id",
        client_secret="your_oauth_client_secret",
        selected_modules=[
            "EmpEmployment",
            "PerPersonal", 
            "EmpJob",
            "User"
        ],
        output_directory="./sap_successfactors_data"
    )
    
    print(f"   🔗 Service URL: {successfactors_config.service_url}")
    print(f"   🔑 Auth Type: OAuth 2.0")
    print(f"   📦 Modules: {', '.join(successfactors_config.selected_modules)}")
    
    # EXAMPLE 3: SAP Ariba OData Service
    print("\n🛒 Example 3: SAP Ariba Procurement")
    ariba_config = ClientConfig(
        service_type=ServiceType.ODATA,
        service_url="https://openapi.ariba.com/api/procurement-reporting/v1/prod/",
        client_id="your_ariba_client_id",
        client_secret="your_ariba_client_secret",
        selected_modules=[
            "PurchaseOrders",
            "Suppliers",
            "Contracts",
            "InvoiceLineItems"
        ],
        output_directory="./sap_ariba_data"
    )
    
    print(f"   🔗 Service URL: {ariba_config.service_url}")
    print(f"   🔑 Auth Type: API Key")
    print(f"   📦 Modules: {', '.join(ariba_config.selected_modules)}")
    
    # EXAMPLE 4: SAP Concur OData Service
    print("\n💳 Example 4: SAP Concur Expense Management")
    concur_config = ClientConfig(
        service_type=ServiceType.ODATA,
        service_url="https://us.api.concursolutions.com/api/v3.0/",
        client_id="your_concur_client_id",
        client_secret="your_concur_client_secret",
        selected_modules=[
            "ExpenseReports",
            "Expenses",
            "Users",
            "Vendors"
        ],
        output_directory="./sap_concur_data"
    )
    
    print(f"   🔗 Service URL: {concur_config.service_url}")
    print(f"   🔑 Auth Type: OAuth 2.0")
    print(f"   📦 Modules: {', '.join(concur_config.selected_modules)}")
    
    print("\n⚠️  Note: These are example configurations.")
    print("   Replace with your actual SAP system details to use.")
    
    return True


async def demonstrate_real_sap_connection():
    """Demonstrate how to actually connect (using test service)"""
    
    print("\n🧪 Actual Connection Test (using Northwind as example)")
    print("=" * 60)
    
    # Use Northwind as a proxy for real SAP system structure
    config = ClientConfig(
        service_type=ServiceType.ODATA,
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=["Products", "Categories", "Suppliers"],  # Specific modules
        output_directory="./real_sap_demo"
    )
    
    print(f"📋 Configuration:")
    print(f"   Service Type: {config.service_type}")
    print(f"   Selected Modules: {', '.join(config.selected_modules)}")
    
    try:
        # Create connector
        connector = SAPODataConnector(config)
        
        # Initialize
        print(f"\n🔧 Initializing connector...")
        entity_info = await connector.initialize()
        
        print(f"✅ Connected successfully!")
        print(f"   Total entities available: {entity_info['total_entities']}")
        print(f"   Selected modules found: {len([e for e in entity_info['entities'] if e['name'] in config.selected_modules])}")
        
        # Get data for specific modules only
        print(f"\n📊 Fetching data for selected modules...")
        result = await connector.get_data(
            selected_entities=config.selected_modules,  # Only fetch selected modules
            record_limit=50,
            batch_size=25,
            max_workers=3,
            requests_per_second=5.0
        )
        
        print(f"✅ Data fetched successfully!")
        print(f"   Entities processed: {len(result['data'])}")
        print(f"   Total records: {result['execution_stats']['records_processed']}")
        print(f"   Duration: {result['execution_stats']['duration_seconds']:.2f}s")
        
        # Show what was fetched
        for entity_name, entity_data in result['data'].items():
            if entity_name in config.selected_modules:
                count = entity_data.get('count', 0)
                print(f"   📦 {entity_name}: {count} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 SAP Real System Connection Examples")
    
    # Show configuration examples
    asyncio.run(connect_to_real_sap())
    
    # Demonstrate actual connection
    success = asyncio.run(demonstrate_real_sap_connection())
    
    print(f"\n🏁 Demo result: {'SUCCESS' if success else 'FAILED'}")
    
    # Clean exit
    import os
    os._exit(0 if success else 1)
