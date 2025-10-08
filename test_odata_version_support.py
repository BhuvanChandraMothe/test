"""Test OData version support"""
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def test_v2_sap():
    """Test OData V2 - SAP EPM Service"""
    print("\n" + "="*70)
    print("TEST 1: OData V2 - SAP EPM Service")
    print("="*70)
    
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./test_v2_sap"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        print(f"✓ Metadata loaded: {len(connector.metadata_service.schemas)} entities")
        
        result = await connector.get_data(
            entity_name="Products",
            record_limit=10
        )
        
        print(f"✓ Records fetched: {result['execution_stats']['records_processed']}")
        print(f"✓ Status: WORKING")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"✗ Status: FAILED")
        return False
    finally:
        await connector.cleanup()


async def test_v2_northwind():
    """Test OData V2 - Northwind Service"""
    print("\n" + "="*70)
    print("TEST 2: OData V2 - Northwind Service")
    print("="*70)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V2/Northwind/Northwind.svc/",
        output_directory="./test_v2_northwind"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        print(f"✓ Metadata loaded: {len(connector.metadata_service.schemas)} entities")
        
        if len(connector.metadata_service.schemas) == 0:
            print(f"✗ No entities found in metadata")
            print(f"✗ Status: METADATA PARSING FAILED")
            return False
        
        result = await connector.get_data(
            entity_name="Products",
            record_limit=10
        )
        
        print(f"✓ Records fetched: {result['execution_stats']['records_processed']}")
        print(f"✓ Status: WORKING")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"✗ Status: FAILED")
        return False
    finally:
        await connector.cleanup()


async def test_v4_northwind():
    """Test OData V4 - Northwind Service"""
    print("\n" + "="*70)
    print("TEST 3: OData V4 - Northwind Service")
    print("="*70)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc/",
        output_directory="./test_v4_northwind"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        print(f"✓ Metadata loaded: {len(connector.metadata_service.schemas)} entities")
        
        if len(connector.metadata_service.schemas) == 0:
            print(f"✗ No entities found in metadata")
            print(f"✗ Status: METADATA PARSING FAILED")
            return False
        
        result = await connector.get_data(
            entity_name="Products",
            record_limit=10
        )
        
        print(f"✓ Records fetched: {result['execution_stats']['records_processed']}")
        
        # Check if we got the expected number
        if result['execution_stats']['records_processed'] == 10:
            print(f"✓ Status: WORKING (Partial V4 support)")
            return True
        else:
            print(f"⚠ Status: PARTIAL (Got {result['execution_stats']['records_processed']} records)")
            return False
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"✗ Status: FAILED")
        return False
    finally:
        await connector.cleanup()


async def main():
    print("\n" + "="*70)
    print("ODATA VERSION SUPPORT TEST")
    print("="*70)
    
    results = {}
    
    # Test V2 SAP
    results['V2_SAP'] = await test_v2_sap()
    
    # Test V2 Northwind
    results['V2_Northwind'] = await test_v2_northwind()
    
    # Test V4 Northwind
    results['V4_Northwind'] = await test_v4_northwind()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\n{'Service':<30} {'Status':<20}")
    print("-" * 50)
    print(f"{'OData V2 - SAP EPM':<30} {'✓ WORKING' if results['V2_SAP'] else '✗ FAILED':<20}")
    print(f"{'OData V2 - Northwind':<30} {'✓ WORKING' if results['V2_Northwind'] else '✗ FAILED':<20}")
    print(f"{'OData V4 - Northwind':<30} {'✓ PARTIAL' if results['V4_Northwind'] else '✗ FAILED':<20}")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    
    if results['V2_SAP']:
        print("✓ Primary Support: OData V2 (SAP Services)")
    
    if results['V2_Northwind']:
        print("✓ OData V2 (Non-SAP) works")
    else:
        print("⚠ OData V2 (Non-SAP) has issues")
    
    if results['V4_Northwind']:
        print("⚠ OData V4 has partial support (may have limitations)")
    else:
        print("✗ OData V4 not fully supported")
    
    print("\nRecommendation: Use OData V2 services for best results")

if __name__ == "__main__":
    asyncio.run(main())
