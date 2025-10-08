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
        print(f"✓ OData Version: {connector.metadata_service.odata_version}")
        
        # Fetch ALL entities - no entity_name means get everything
        print("\n1. Fetching ALL entities from Northwind V4...")
        print("   (This will take a while - ~11,400 records from 26 entities)")
        
        # Use entity_name instead of selected_entities to use the fixed pagination path
        result = await connector.get_data(entity_name="Summary_of_Sales_by_Quarters")
        
        total_records = result['execution_stats']['records_processed']
        total_entities = result['execution_stats']['entities_processed']
        duration = result['execution_stats']['duration_seconds']
        
        print(f"\n✓ Total records fetched: {total_records:,}")
        print(f"✓ Total entities processed: {total_entities}")
        print(f"✓ Duration: {duration:.1f} seconds")
        print(f"✓ Rate: {total_records/duration:.0f} records/second")
        
        # Summary
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"Total Records: {total_records:,}")
        print(f"Total Entities: {total_entities}")
        print(f"Expected: 2,155 Invoices")
        
        if total_records >= 2155:
            print("\n🎉 SUCCESS! Fetched ALL Invoices from Northwind V4!")
            return True
        else:
            print(f"\n⚠️ Partial: Got {total_records:,}/2,155 records")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await connector.cleanup()

if __name__ == "__main__":
    success = asyncio.run(test_v4_full())
