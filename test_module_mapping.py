"""
Quick test for SAP Module Mapping functionality
Tests the ES5 module with your existing credentials
"""

import asyncio
from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector
from odc.config.sap_module_mapping import SAPModuleMapping


async def test_es5_module_mapping():
    """Test ES5 module mapping with existing credentials"""
    
    print("=" * 80)
    print("  SAP Module Mapping Test - ES5 Demo System")
    print("=" * 80)
    
    # Method 1: Using sap_module parameter (NEW!)
    print("\n✓ Method 1: Using sap_module parameter")
    config1 = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        sap_module="ES5",  # Automatically mapped to EPM_REF_APPS_SHOP_SRV
        use_https=True,
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./output_module_test"
    )
    
    print(f"  Module: ES5")
    print(f"  Mapped to: {SAPModuleMapping.get_service_name('ES5')}")
    print(f"  URL: {config1.odata_service_url}")
    
    # Method 2: Using service_name with module name (auto-detected)
    print("\n✓ Method 2: Using service_name with module name (auto-detected)")
    config2 = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        service_name="ES",  # Will be auto-detected as module and mapped
        use_https=True,
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./output_module_test"
    )
    
    print(f"  Input: ES5 (in service_name)")
    print(f"  Detected as module, mapped to: {SAPModuleMapping.get_service_name('ES5')}")
    print(f"  URL: {config2.odata_service_url}")
    
    # Method 3: Legacy mode (for comparison)
    print("\n✓ Method 3: Legacy mode (direct URL)")
    config3 = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./output_module_test"
    )
    
    print(f"  URL: {config3.odata_service_url}")
    
    # Verify all three methods produce the same URL
    print("\n" + "=" * 80)
    print("  URL Comparison")
    print("=" * 80)
    
    url1 = config1.odata_service_url.rstrip('/')
    url2 = config2.odata_service_url.rstrip('/')
    url3 = config3.odata_service_url.rstrip('/')
    
    print(f"  Method 1 (sap_module):    {url1}")
    print(f"  Method 2 (auto-detect):   {url2}")
    print(f"  Method 3 (legacy):        {url3}")
    
    if url1 == url2 == url3:
        print("\n  ✅ All methods produce the same URL!")
    else:
        print("\n  ⚠️  URLs differ!")
    
    # Test actual connection with Method 1 (module mapping)
    print("\n" + "=" * 80)
    print("  Testing Connection with Module Mapping")
    print("=" * 80)
    
    connector = SAPODataConnector(config1)
    
    try:
        # Initialize and test connection
        print("\n⏳ Initializing connector...")
        await connector.initialize()
        print("✅ Connection successful!")
        print("✅ Credentials validated!")
        
        # Get some sample data
        print("\n⏳ Fetching sample products...")
        result = await connector.get_data(
            entity_name="Products",
            select_fields="Id,Name,Price,CurrencyCode",
            record_limit=5
        )
        
        records_count = result['execution_stats']['records_processed']
        print(f"✅ Retrieved {records_count} products")
        
        # Display sample data
        if 'Products' in result['data'] and result['data']['Products']['records']:
            print("\n📦 Sample Products:")
            for i, record in enumerate(result['data']['Products']['records'][:3], 1):
                if hasattr(record, 'data'):
                    data = record.data
                else:
                    data = record
                
                name = data.get('Name', 'N/A')
                price = data.get('Price', 'N/A')
                currency = data.get('CurrencyCode', 'N/A')
                print(f"  {i}. {name} - {price} {currency}")
        
        print("\n" + "=" * 80)
        print("  ✅ Module Mapping Test PASSED!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n" + "=" * 80)
        print("  ❌ Module Mapping Test FAILED")
        print("=" * 80)
    
    finally:
        await connector.cleanup()


def test_module_info():
    """Test module information retrieval"""
    print("\n" + "=" * 80)
    print("  SAP Module Information")
    print("=" * 80)
    
    test_modules = ["ES5", "FI", "MM", "SD", "ARIBA", "CONCUR"]
    
    for module in test_modules:
        info = SAPModuleMapping.get_module_info(module)
        if info:
            print(f"\n  Module: {module}")
            print(f"    Service Name: {info['service_name']}")
            print(f"    Category: {info['category']}")
            print(f"    Is Cloud: {info['is_cloud']}")
            print(f"    Is Demo: {info['is_demo']}")


def test_module_search():
    """Test module search functionality"""
    print("\n" + "=" * 80)
    print("  SAP Module Search")
    print("=" * 80)
    
    search_terms = ["FI", "MM", "ARIBA"]
    
    for term in search_terms:
        results = SAPModuleMapping.search_modules(term)
        print(f"\n  Search '{term}': Found {len(results)} modules")
        for module in results[:5]:
            service = SAPModuleMapping.get_service_name(module)
            print(f"    • {module:20} → {service}")


async def main():
    """Main test function"""
    print("\n" + "█" * 80)
    print("  SAP OData Connector - Module Mapping Test Suite")
    print("█" * 80)
    
    # Test module info
    test_module_info()
    
    # Test module search
    test_module_search()
    
    # Test ES5 connection with module mapping
    await test_es5_module_mapping()
    
    print("\n" + "█" * 80)
    print("  All Tests Completed!")
    print("█" * 80)


if __name__ == "__main__":
    print("\n🚀 Starting SAP Module Mapping Tests...")
    asyncio.run(main())
    print("\n✅ Test execution complete!")
