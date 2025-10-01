"""
Test file for enhanced SAP OData Connector features.
Tests the new SAP connection parameters and advanced OData query options.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import odc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector


async def test_sap_url_construction():
    """Test 1: SAP URL auto-construction"""
    print("🧪 Test 1: SAP URL Auto-construction")
    
    # Test new parameter approach
    config = ClientConfig(
        sap_server="demo-server.sap.com",
        sap_port=8000,
        service_name="NORTHWIND_SRV",
        use_https=True,
        username="demo",
        password="demo",
        sap_client="100",
        selected_modules=["Products"]
    )
    
    expected_url = "https://demo-server.sap.com:8000/sap/opu/odata/sap/NORTHWIND_SRV"
    actual_url = config.odata_service_url
    
    assert actual_url == expected_url, f"Expected {expected_url}, got {actual_url}"
    print(f" URL construction works: {actual_url}")
    
    # Test entity set URL
    entity_url = config.get_entity_set_url("Products")
    expected_entity_url = f"{expected_url}/Products"
    assert entity_url == expected_entity_url, f"Expected {expected_entity_url}, got {entity_url}"
    print(f" Entity URL construction works: {entity_url}")


async def test_legacy_url_compatibility():
    """Test 2: Legacy URL compatibility"""
    print("\n🧪 Test 2: Legacy URL Compatibility")
    
    # Test legacy approach
    legacy_config = ClientConfig(
        service_url="https://services.odata.org/V2/Northwind/Northwind.svc",
        username="demo",
        password="demo",
        selected_modules=["Products"]
    )
    
    expected_url = "https://services.odata.org/V2/Northwind/Northwind.svc"
    actual_url = legacy_config.odata_service_url
    
    assert actual_url == expected_url, f"Expected {expected_url}, got {actual_url}"
    print(f" Legacy URL compatibility works: {actual_url}")


async def test_query_options_structure():
    """Test 3: Query options structure"""
    print("\n🧪 Test 3: Query Options Structure")
    
    from odc.planning.plan_generator import FetchCommand, CommandType, Priority
    
    # Test enhanced FetchCommand
    command = FetchCommand(
        command_id="test_cmd",
        command_type=CommandType.FETCH_PAGE,
        entity_set="Products",
        skip=0,
        top=10,
        filter_clause="UnitPrice gt 20",
        select_clause="ProductID,ProductName,UnitPrice",
        orderby_clause="UnitPrice desc",
        expand_clause="Category,Supplier",
        groupby_clause="CategoryID",
        aggregate_clause="sum(UnitPrice) as TotalPrice",
        count_option=True,
        search_clause="chocolate",
        custom_params={"sap-client": "100"}
    )
    
    params = command.url_params
    
    # Verify all parameters are included
    expected_params = {
        '$skip': '0',
        '$top': '10',
        '$filter': 'UnitPrice gt 20',
        '$select': 'ProductID,ProductName,UnitPrice',
        '$orderby': 'UnitPrice desc',
        '$expand': 'Category,Supplier',
        '$search': 'chocolate',
        '$count': 'true',
        '$apply': 'groupby((CategoryID)),aggregate(sum(UnitPrice) as TotalPrice)',
        'sap-client': '100'
    }
    
    for key, value in expected_params.items():
        assert key in params, f"Missing parameter: {key}"
        assert params[key] == value, f"Parameter {key}: expected {value}, got {params[key]}"
    
    print(f" Query options structure works: {len(params)} parameters generated")
    print(f"   Parameters: {list(params.keys())}")


async def test_config_validation():
    """Test 4: Configuration validation"""
    print("\n🧪 Test 4: Configuration Validation")
    
    # Test valid new config
    try:
        valid_config = ClientConfig(
            sap_server="test-server.com",
            sap_port=8000,
            service_name="TEST_SRV",
            use_https=True,
            username="test",
            password="test"
        )
        valid_config.validate()
        print(" Valid new config passes validation")
    except Exception as e:
        print(f"❌ Valid config failed validation: {e}")
        raise
    
    # Test valid legacy config
    try:
        legacy_config = ClientConfig(
            service_url="https://test.com/service",
            username="test",
            password="test"
        )
        legacy_config.validate()
        print(" Valid legacy config passes validation")
    except Exception as e:
        print(f"❌ Valid legacy config failed validation: {e}")
        raise
    
    # Test invalid configs
    try:
        invalid_config = ClientConfig(
            sap_server="",  # Empty server
            service_name="TEST_SRV",
            username="test",
            password="test"
        )
        invalid_config.validate()
        print("❌ Invalid config should have failed validation")
        assert False, "Invalid config should have failed"
    except ValueError:
        print(" Invalid config correctly rejected")


async def test_northwind_connection():
    """Test 5: Real connection to Northwind service"""
    print("\n🧪 Test 5: Real Northwind Connection")
    
    # Use public Northwind service for testing
    config = ClientConfig(
        service_url="https://services.odata.org/V2/Northwind/Northwind.svc",
        output_directory="./test_output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        # Test initialization
        print("   Initializing connector...")
        entity_info = await connector.initialize()
        print(f" Initialization successful: {entity_info['total_entities']} entities found")
        
        # Get the first available entity for testing
        available_entities = list(entity_info['entities'])
        if not available_entities:
            print("❌ No entities available for testing")
            return
        
        test_entity = available_entities[0]['name']
        print(f"   Testing with entity: {test_entity}")
        
        # Test basic query with new options
        print("   Testing enhanced query options...")
        result = await connector.get_data(
            entity_name=test_entity,
            record_limit=5,
            batch_size=3,
            max_workers=2
        )
        
        records_processed = result['execution_stats']['records_processed']
        duration = result['execution_stats']['duration_seconds']
        
        print(f" Enhanced query successful: {records_processed} records in {duration:.2f}s")
        
        # Verify data structure
        if test_entity in result['data']:
            entity_data = result['data'][test_entity]['records']
            if entity_data:
                sample_record = entity_data[0]
                print(f" Data structure correct: {len(entity_data)} {test_entity} records")
                print(f"   Sample record keys: {list(sample_record.keys())[:5]}...")  # First 5 fields
            else:
                print(f"⚠️ No data returned for {test_entity}")
        else:
            print(f"⚠️ Entity {test_entity} not found in result data")
        
    except Exception as e:
        print(f"❌ Northwind connection test failed: {e}")
        raise
    
    finally:
        await connector.cleanup()


async def run_all_tests():
    """Run all tests"""
    print(" Enhanced SAP OData Connector - Test Suite")
    print("=" * 50)
    
    tests = [
        test_sap_url_construction,
        test_legacy_url_compatibility,
        test_query_options_structure,
        test_config_validation,
        test_northwind_connection
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Enhanced features are working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
