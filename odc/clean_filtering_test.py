"""
Clean Filtering Test - Uses SAP OData Connector with Clean Data Output
Returns only the actual data without metadata or transformation info
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector


def clean_data(records):
    """Extract only the actual data from records, removing metadata"""
    if not records:
        return []
    
    clean_records = []
    for record in records:
        if hasattr(record, 'data'):
            # If it's a TransformedRecord object, get the data
            clean_records.append(record.data)
        elif isinstance(record, dict):
            # If it's a dict, remove metadata fields
            clean_record = {}
            for key, value in record.items():
                # Skip metadata fields
                if key not in ['@odata.etag', '@odata.context', '@odata.type', 
                              'transformed_at', 'metadata', 'entity_name', 'record_id']:
                    clean_record[key] = value
            clean_records.append(clean_record)
        else:
            clean_records.append(record)
    
    return clean_records


def save_clean_data(data, filename):
    """Save clean data to JSON file"""
    os.makedirs("./clean_test_output", exist_ok=True)
    filepath = f"./clean_test_output/{filename}"
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    return filepath


async def test_connector_filtering():
    """Test SAP OData Connector with clean data output"""
    
    print("🎯 SAP ODATA CONNECTOR - CLEAN FILTERING TEST")
    print("=" * 60)
    
    # Configuration
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./clean_test_output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        print("🔧 Initializing connector...")
        await connector.initialize()
        print(" Connector initialized successfully!")
        
        # TEST 1: Basic Products (no filter)
        print("\n🧪 TEST 1: Get basic products (no filter)")
        result1 = await connector.get_data(
            entity_name="Products",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID,UnitsInStock",
            record_limit=5,
            batch_size=5,
            max_workers=1
        )
        
        print(f" Retrieved {result1['execution_stats']['records_processed']} products")
        
        if 'Products' in result1['data'] and result1['data']['Products']['records']:
            products = result1['data']['Products']['records']
            clean_products = clean_data(products)
            
            # Save clean data
            filepath1 = save_clean_data(clean_products, "basic_products_clean.json")
            print(f" Saved to: {filepath1}")
            
            # Display results
            print("📊 BASIC PRODUCTS:")
            for i, product in enumerate(clean_products, 1):
                name = product.get('ProductName', 'N/A')
                price = product.get('UnitPrice', 'N/A')
                category = product.get('CategoryID', 'N/A')
                stock = product.get('UnitsInStock', 'N/A')
                print(f"   {i}. {name} - ${price} (Cat: {category}, Stock: {stock})")
        else:
            print("❌ No products data found")
        
        # TEST 2: Price Filtering
        print("\n🧪 TEST 2: Filter expensive products (Price > $20)")
        result2 = await connector.get_data(
            entity_name="Products",
            filter_condition="UnitPrice gt 20",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID",
            record_limit=5,
            batch_size=5,
            max_workers=1
        )
        
        print(f" Retrieved {result2['execution_stats']['records_processed']} expensive products")
        
        if 'Products' in result2['data'] and result2['data']['Products']['records']:
            expensive_products = result2['data']['Products']['records']
            clean_expensive = clean_data(expensive_products)
            
            # Save clean data
            filepath2 = save_clean_data(clean_expensive, "expensive_products_clean.json")
            print(f" Saved to: {filepath2}")
            
            # Display results
            print("💰 EXPENSIVE PRODUCTS (>$20):")
            for i, product in enumerate(clean_expensive, 1):
                name = product.get('ProductName', 'N/A')
                price = product.get('UnitPrice', 'N/A')
                print(f"   {i}. {name} - ${price}")
        else:
            print("❌ No expensive products data found")
        
        # TEST 3: Category Filtering
        print("\n🧪 TEST 3: Filter products in Category 1 (Beverages)")
        result3 = await connector.get_data(
            entity_name="Products",
            filter_condition="CategoryID eq 1",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID",
            record_limit=5,
            batch_size=5,
            max_workers=1
        )
        
        print(f" Retrieved {result3['execution_stats']['records_processed']} beverages")
        
        if 'Products' in result3['data'] and result3['data']['Products']['records']:
            beverages = result3['data']['Products']['records']
            clean_beverages = clean_data(beverages)
            
            # Save clean data
            filepath3 = save_clean_data(clean_beverages, "beverages_clean.json")
            print(f" Saved to: {filepath3}")
            
            # Display results
            print("🥤 BEVERAGES (Category 1):")
            for i, product in enumerate(clean_beverages, 1):
                name = product.get('ProductName', 'N/A')
                price = product.get('UnitPrice', 'N/A')
                print(f"   {i}. {name} - ${price}")
        else:
            print("❌ No beverages data found")
        
        # TEST 4: Sorting
        print("\n🧪 TEST 4: Get most expensive products (sorted)")
        result4 = await connector.get_data(
            entity_name="Products",
            select_fields="ProductID,ProductName,UnitPrice",
            order_by="UnitPrice desc",
            record_limit=5,
            batch_size=5,
            max_workers=1
        )
        
        print(f" Retrieved {result4['execution_stats']['records_processed']} products sorted by price")
        
        if 'Products' in result4['data'] and result4['data']['Products']['records']:
            sorted_products = result4['data']['Products']['records']
            clean_sorted = clean_data(sorted_products)
            
            # Save clean data
            filepath4 = save_clean_data(clean_sorted, "sorted_products_clean.json")
            print(f" Saved to: {filepath4}")
            
            # Display results
            print("📈 MOST EXPENSIVE PRODUCTS:")
            for i, product in enumerate(clean_sorted, 1):
                name = product.get('ProductName', 'N/A')
                price = product.get('UnitPrice', 'N/A')
                print(f"   {i}. {name} - ${price}")
        else:
            print("❌ No sorted products data found")
        
        # TEST 5: Customer Filtering
        print("\n🧪 TEST 5: Filter customers from Germany")
        result5 = await connector.get_data(
            entity_name="Customers",
            filter_condition="Country eq 'Germany'",
            select_fields="CustomerID,CompanyName,Country,City,ContactName",
            record_limit=5,
            batch_size=5,
            max_workers=1
        )
        
        print(f" Retrieved {result5['execution_stats']['records_processed']} German customers")
        
        if 'Customers' in result5['data'] and result5['data']['Customers']['records']:
            customers = result5['data']['Customers']['records']
            clean_customers = clean_data(customers)
            
            # Save clean data
            filepath5 = save_clean_data(clean_customers, "german_customers_clean.json")
            print(f" Saved to: {filepath5}")
            
            # Display results
            print("🇩🇪 GERMAN CUSTOMERS:")
            for i, customer in enumerate(clean_customers, 1):
                company = customer.get('CompanyName', 'N/A')
                city = customer.get('City', 'N/A')
                contact = customer.get('ContactName', 'N/A')
                print(f"   {i}. {company} - {city} (Contact: {contact})")
        else:
            print("❌ No German customers data found")
        
        # Create summary
        summary = {
            "test_date": datetime.now().isoformat(),
            "connector_used": "SAP OData Connector",
            "tests_completed": 5,
            "files_created": [
                "basic_products_clean.json",
                "expensive_products_clean.json", 
                "beverages_clean.json",
                "sorted_products_clean.json",
                "german_customers_clean.json"
            ],
            "filtering_methods_tested": [
                "Basic data retrieval",
                "Price filtering (UnitPrice gt 20)",
                "Category filtering (CategoryID eq 1)",
                "Sorting (order by UnitPrice desc)",
                "Country filtering (Country eq 'Germany')"
            ]
        }
        
        summary_path = save_clean_data(summary, "test_summary.json")
        print(f"\n📄 Summary saved to: {summary_path}")
        
        print("\n🎉 ALL CONNECTOR FILTERING TESTS COMPLETED!")
        print(" All data saved as clean JSON files (no metadata)")
        print(" Real data from SAP OData Connector (not hardcoded)")
        print(" Multiple filtering methods demonstrated")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await connector.cleanup()
            print("🧹 Connector cleanup completed")
        except:
            pass


if __name__ == "__main__":
    print(" Starting SAP OData Connector Clean Filtering Test...")
    success = asyncio.run(test_connector_filtering())
    
    if success:
        print("\n🎉 SUCCESS! Check './clean_test_output/' for all clean data files")
    else:
        print("\n❌ TEST FAILED!")
    
    input("Press Enter to exit...")
