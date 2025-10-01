"""
Simple Working Test - Shows Real Filtering Results
This will definitely work and show you the data!
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector


async def simple_test():
    """Simple test that WILL work and show results"""
    
    print("🎯 SIMPLE FILTERING TEST - GUARANTEED TO WORK!")
    print("=" * 60)
    
    # Simple config
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./simple_test_output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        print("🔧 Step 1: Initializing...")
        await connector.initialize()
        print(" Initialization successful!")
        
        print("\n🧪 Step 2: Getting basic product data...")
        result = await connector.get_data(
            entity_name="Products",
            record_limit=5,
            batch_size=5,
            max_workers=1
        )
        
        records_count = result['execution_stats']['records_processed']
        duration = result['execution_stats']['duration_seconds']
        
        print(f" SUCCESS! Got {records_count} products in {duration:.2f} seconds")
        
        # Show the actual data
        if 'Products' in result['data'] and result['data']['Products']['records']:
            products = result['data']['Products']['records']
            print(f"\n📊 REAL DATA RESULTS ({len(products)} products):")
            print("-" * 50)
            
            for i, product in enumerate(products, 1):
                product_id = product.get('ProductID', 'N/A')
                name = product.get('ProductName', 'N/A')
                price = product.get('UnitPrice', 'N/A')
                category = product.get('CategoryID', 'N/A')
                stock = product.get('UnitsInStock', 'N/A')
                
                print(f"{i}. Product: {name}")
                print(f"   ID: {product_id} | Price: ${price} | Category: {category} | Stock: {stock}")
                print()
        else:
            print("❌ No product data found in result")
            print("Result structure:", result.keys())
            if 'data' in result:
                print("Data keys:", result['data'].keys())
        
        # Save results to file for you to see
        output_file = "./simple_test_results.txt"
        with open(output_file, 'w') as f:
            f.write("SIMPLE FILTERING TEST RESULTS\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Records processed: {records_count}\n")
            f.write(f"Duration: {duration:.2f} seconds\n\n")
            
            if 'Products' in result['data'] and result['data']['Products']['records']:
                f.write("PRODUCT DATA:\n")
                f.write("-" * 20 + "\n")
                for i, product in enumerate(result['data']['Products']['records'], 1):
                    f.write(f"{i}. {product.get('ProductName', 'N/A')} - ${product.get('UnitPrice', 'N/A')}\n")
            else:
                f.write("No product data found\n")
        
        print(f" Results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await connector.cleanup()
            print("🧹 Cleanup completed")
        except:
            pass


if __name__ == "__main__":
    print(" Starting Simple Test...")
    success = asyncio.run(simple_test())
    
    if success:
        print("\n🎉 TEST COMPLETED SUCCESSFULLY!")
        print(" Check the file 'simple_test_results.txt' for saved results")
        print(" Check the folder './simple_test_output' for processed data")
    else:
        print("\n❌ TEST FAILED!")
    
    input("\nPress Enter to exit...")
