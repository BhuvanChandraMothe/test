"""
SAP OData Connector - Module-Based Configuration Examples

This file demonstrates how to use the SAP module mapping feature to automatically
construct OData service URLs from SAP module names.

The connector now supports three ways to configure the connection:
1. Direct service URL (legacy mode)
2. Server + Service Name (manual mode)
3. Server + Module Name (automatic mapping mode) - NEW!
"""

import asyncio
from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector
from odc.config.sap_module_mapping import SAPModuleMapping


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def example_1_legacy_mode():
    """Example 1: Legacy mode - Direct service URL"""
    print_section("Example 1: Legacy Mode - Direct Service URL")
    
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    print(f"✓ Service URL: {config.odata_service_url}")
    print("✓ Mode: Legacy (direct URL)")


def example_2_manual_service_name():
    """Example 2: Manual mode - Server + Service Name"""
    print_section("Example 2: Manual Mode - Server + Service Name")
    
    config = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        service_name="EPM_REF_APPS_SHOP_SRV",
        use_https=True,
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    print(f"✓ Service URL: {config.odata_service_url}")
    print("✓ Mode: Manual (server + service name)")


def example_3_module_mapping_es5():
    """Example 3: Module mapping - ES5 Demo System"""
    print_section("Example 3: Module Mapping - ES5 Demo System")
    
    # Using sap_module parameter
    config = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        sap_module="ES5",  # Will be mapped to EPM_REF_APPS_SHOP_SRV
        use_https=True,
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    print(f"✓ Module: ES5")
    print(f"✓ Mapped Service: EPM_REF_APPS_SHOP_SRV")
    print(f"✓ Service URL: {config.odata_service_url}")
    print(f"✓ Module Info: {config.get_module_info()}")


def example_4_module_mapping_finance():
    """Example 4: Module mapping - Finance (FI) Module"""
    print_section("Example 4: Module Mapping - Finance (FI) Module")
    
    config = ClientConfig(
        sap_server="your-sap-server.com",
        sap_port=8000,
        sap_module="FI",  # Will be mapped to FINS_GENERALLEDGER_SRV
        sap_client="100",  # SAP client number
        use_https=True,
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    print(f"✓ Module: FI")
    print(f"✓ Mapped Service: FINS_GENERALLEDGER_SRV")
    print(f"✓ Service URL: {config.odata_service_url}")
    print(f"✓ SAP Client: {config.sap_client}")


def example_5_module_mapping_ariba():
    """Example 5: Module mapping - Ariba Procurement"""
    print_section("Example 5: Module Mapping - Ariba Procurement")
    
    config = ClientConfig(
        sap_server="ariba-server.com",
        sap_port=443,
        sap_module="ARIBA",  # Will be mapped to ARIBA_PROCUREMENT_SRV
        use_https=True,
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    print(f"✓ Module: ARIBA")
    print(f"✓ Mapped Service: ARIBA_PROCUREMENT_SRV")
    print(f"✓ Service URL: {config.odata_service_url}")


def example_6_module_mapping_concur():
    """Example 6: Module mapping - Concur Expense"""
    print_section("Example 6: Module Mapping - Concur Expense")
    
    config = ClientConfig(
        sap_server="concur-server.com",
        sap_port=443,
        sap_module="CONCUR",  # Will be mapped to CONCUR_EXPENSE_SRV
        use_https=True,
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    print(f"✓ Module: CONCUR")
    print(f"✓ Mapped Service: CONCUR_EXPENSE_SRV")
    print(f"✓ Service URL: {config.odata_service_url}")


def example_7_auto_detect_module_in_service_name():
    """Example 7: Auto-detect module name in service_name field"""
    print_section("Example 7: Auto-detect Module Name in service_name Field")
    
    # Even if you put module name in service_name field, it will be auto-detected
    config = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        service_name="ES5",  # Will be detected as module and mapped
        use_https=True,
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    print(f"✓ Input (service_name): ES5")
    print(f"✓ Detected as module, mapped to: EPM_REF_APPS_SHOP_SRV")
    print(f"✓ Service URL: {config.odata_service_url}")


def example_8_list_all_modules():
    """Example 8: List all supported SAP modules"""
    print_section("Example 8: List All Supported SAP Modules")
    
    all_modules = SAPModuleMapping.get_all_modules()
    
    print(f"✓ Total supported modules: {len(all_modules)}")
    print("\n📋 Sample modules:")
    
    # Group by category
    categories = {
        "Finance": ["FI", "FI-GL", "FI-AP", "FI-AR", "CO"],
        "Logistics": ["MM", "MM-PUR", "SD", "SD-SO", "PP"],
        "HR": ["HR", "HR-PA", "SF", "SUCCESSFACTORS"],
        "Cloud/Procurement": ["ARIBA", "CONCUR", "ARIBA-BUYER"],
        "Demo/Testing": ["ES5", "EPM", "DEMO", "GWSAMPLE"]
    }
    
    for category, modules in categories.items():
        print(f"\n  {category}:")
        for module in modules:
            service = SAPModuleMapping.get_service_name(module)
            print(f"    • {module:20} → {service}")


def example_9_search_modules():
    """Example 9: Search for modules"""
    print_section("Example 9: Search for Modules")
    
    search_terms = ["FI", "ARIBA", "HR", "MM"]
    
    for term in search_terms:
        results = SAPModuleMapping.search_modules(term)
        print(f"\n🔍 Search '{term}': Found {len(results)} modules")
        for module in results[:5]:  # Show first 5
            service = SAPModuleMapping.get_service_name(module)
            print(f"    • {module:20} → {service}")


async def example_10_real_connection_test():
    """Example 10: Real connection test with ES5 module"""
    print_section("Example 10: Real Connection Test with ES5 Module")
    
    # NOTE: Replace with your actual ES5 credentials
    config = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        sap_module="ES5",  # Automatically mapped to EPM_REF_APPS_SHOP_SRV
        use_https=True,
        username="YOUR_ES5_USERNAME",  # Replace with your ES5 username
        password="YOUR_ES5_PASSWORD",  # Replace with your ES5 password
        output_directory="./output_es5"
    )
    
    print(f"✓ Module: ES5")
    print(f"✓ Mapped Service: {SAPModuleMapping.get_service_name('ES5')}")
    print(f"✓ Service URL: {config.odata_service_url}")
    print(f"✓ Module Info: {config.get_module_info()}")
    
    print("\n⚠️  To test connection, replace credentials and uncomment the code below:")
    print("""
    # Uncomment to test:
    # connector = SAPODataConnector(config)
    # try:
    #     await connector.initialize()
    #     print("✓ Connection successful!")
    #     
    #     # Get some data
    #     result = await connector.get_data(
    #         entity_name="Products",
    #         record_limit=5
    #     )
    #     print(f"✓ Retrieved {result['execution_stats']['records_processed']} products")
    # finally:
    #     await connector.cleanup()
    """)


def example_11_multiple_modules():
    """Example 11: Working with multiple SAP modules"""
    print_section("Example 11: Multiple Module Configurations")
    
    modules_to_test = ["FI", "MM", "SD", "ARIBA", "CONCUR", "ES5"]
    
    print("\n📦 Module Configurations:\n")
    
    for module in modules_to_test:
        service_name = SAPModuleMapping.get_service_name(module)
        module_info = SAPModuleMapping.get_module_info(module)
        
        print(f"  {module:15} → {service_name}")
        if module_info:
            print(f"  {'':15}   Category: {module_info['category']}")
            print(f"  {'':15}   Cloud: {module_info['is_cloud']}")
            print(f"  {'':15}   Demo: {module_info['is_demo']}")
        print()


def main():
    """Run all examples"""
    print("\n" + "█" * 80)
    print("  SAP OData Connector - Module-Based Configuration Examples")
    print("█" * 80)
    
    # Configuration examples
    example_1_legacy_mode()
    example_2_manual_service_name()
    example_3_module_mapping_es5()
    example_4_module_mapping_finance()
    example_5_module_mapping_ariba()
    example_6_module_mapping_concur()
    example_7_auto_detect_module_in_service_name()
    
    # Module discovery examples
    example_8_list_all_modules()
    example_9_search_modules()
    example_11_multiple_modules()
    
    # Connection test example (async)
    print("\n" + "=" * 80)
    print("  Example 10: Connection Test (requires async)")
    print("=" * 80)
    print("  Run this example separately with: asyncio.run(example_10_real_connection_test())")
    
    print("\n" + "█" * 80)
    print("  ✓ All examples completed!")
    print("█" * 80)
    
    print("\n📚 Key Takeaways:")
    print("  1. Use 'sap_module' parameter for automatic service name mapping")
    print("  2. Supports 50+ SAP modules (FI, MM, SD, ARIBA, CONCUR, ES5, etc.)")
    print("  3. Automatically constructs SAP OData URLs")
    print("  4. Validates credentials by testing metadata endpoint")
    print("  5. Backward compatible with direct service_url")


if __name__ == "__main__":
    main()
    
    # To run the async example:
    # asyncio.run(example_10_real_connection_test())
