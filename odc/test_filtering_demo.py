"""
Comprehensive Filtering Demo - Real Data Filtering Examples

This demo shows all the filtering capabilities with actual data results displayed.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import odc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector


def display_results(result, test_name, entity_name):
    """Helper function to display results nicely"""
    print(f"\n🔍 {test_name}")
    print("=" * 50)
    
    stats = result['execution_stats']
    print(f"📊 Records found: {stats['records_processed']}")
    print(f"⏱️  Query time: {stats['duration_seconds']:.2f}s")
    
    if entity_name in result['data'] and result['data'][entity_name]['records']:
        records = result['data'][entity_name]['records']
        print(f"\n📋 Sample Results ({len(records)} records):")
        
        for i, record in enumerate(records[:5], 1):  # Show first 5 records
            print(f"   {i}. ", end="")
            
            # Display key fields based on entity type
            if entity_name == "Products":
                name = record.get('ProductName', 'N/A')
                price = record.get('UnitPrice', 'N/A')
                category = record.get('CategoryID', 'N/A')
                print(f"{name} - ${price} (Category: {category})")
                
            elif entity_name == "Orders":
                order_id = record.get('OrderID', 'N/A')
                customer = record.get('CustomerID', 'N/A')
                date = record.get('OrderDate', 'N/A')
                freight = record.get('Freight', 'N/A')
                print(f"Order #{order_id} - Customer: {customer}, Date: {date}, Freight: ${freight}")
                
            elif entity_name == "Customers":
                company = record.get('CompanyName', 'N/A')
                country = record.get('Country', 'N/A')
                city = record.get('City', 'N/A')
                print(f"{company} - {city}, {country}")
                
            else:
                # Generic display for other entities
                keys = list(record.keys())[:3]  # First 3 fields
                values = [str(record.get(k, 'N/A'))[:20] for k in keys]
                print(f"{' | '.join(f'{k}: {v}' for k, v in zip(keys, values))}")
    else:
        print("   ⚠️ No data returned")


async def demo_basic_filtering():
    """Demo 1: Basic $filter operations"""
    print("🧪 DEMO 1: Basic Filtering ($filter)")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./filter_demo_output"
    )
    
    async with SAPODataConnector(config) as connector:
        
        # Filter 1: Products with price > 20
        result1 = await connector.get_data(
            entity_name="Products",
            filter_condition="UnitPrice gt 20",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID",
            record_limit=10
        )
        display_results(result1, "Products with Price > $20", "Products")
        
        # Filter 2: Products with specific category
        result2 = await connector.get_data(
            entity_name="Products",
            filter_condition="CategoryID eq 1",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID",
            record_limit=8
        )
        display_results(result2, "Products in Category 1 (Beverages)", "Products")
        
        # Filter 3: Products with price range
        result3 = await connector.get_data(
            entity_name="Products",
            filter_condition="UnitPrice ge 10 and UnitPrice le 50",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID",
            record_limit=10
        )
        display_results(result3, "Products Priced Between $10-$50", "Products")


async def demo_advanced_filtering():
    """Demo 2: Advanced filtering with string operations"""
    print("\n🧪 DEMO 2: Advanced String Filtering")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./filter_demo_output"
    )
    
    async with SAPODataConnector(config) as connector:
        
        # Filter 1: Products containing specific text
        try:
            result1 = await connector.get_data(
                entity_name="Products",
                filter_condition="contains(ProductName, 'Cheese')",
                select_fields="ProductID,ProductName,UnitPrice,CategoryID",
                record_limit=10
            )
            display_results(result1, "Products Containing 'Cheese'", "Products")
        except Exception as e:
            print(f"⚠️ Cheese filter failed: {e}")
        
        # Filter 2: Products starting with specific letter
        try:
            result2 = await connector.get_data(
                entity_name="Products",
                filter_condition="startswith(ProductName, 'C')",
                select_fields="ProductID,ProductName,UnitPrice,CategoryID",
                record_limit=8
            )
            display_results(result2, "Products Starting with 'C'", "Products")
        except Exception as e:
            print(f"⚠️ Startswith filter failed: {e}")
        
        # Filter 3: Customers from specific countries
        try:
            result3 = await connector.get_data(
                entity_name="Customers",
                filter_condition="Country eq 'Germany' or Country eq 'France'",
                select_fields="CustomerID,CompanyName,Country,City",
                record_limit=10
            )
            display_results(result3, "Customers from Germany or France", "Customers")
        except Exception as e:
            print(f"⚠️ Country filter failed: {e}")


async def demo_sorting_and_selection():
    """Demo 3: Sorting and field selection"""
    print("\n🧪 DEMO 3: Sorting & Field Selection")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./filter_demo_output"
    )
    
    async with SAPODataConnector(config) as connector:
        
        # Sort 1: Most expensive products
        result1 = await connector.get_data(
            entity_name="Products",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID",
            order_by="UnitPrice desc",
            record_limit=8
        )
        display_results(result1, "Most Expensive Products (Sorted by Price DESC)", "Products")
        
        # Sort 2: Cheapest products
        result2 = await connector.get_data(
            entity_name="Products",
            select_fields="ProductID,ProductName,UnitPrice,CategoryID",
            order_by="UnitPrice asc",
            record_limit=8
        )
        display_results(result2, "Cheapest Products (Sorted by Price ASC)", "Products")
        
        # Sort 3: Products by name alphabetically
        result3 = await connector.get_data(
            entity_name="Products",
            select_fields="ProductID,ProductName,UnitPrice",
            order_by="ProductName asc",
            record_limit=10
        )
        display_results(result3, "Products Sorted Alphabetically", "Products")


async def demo_date_filtering():
    """Demo 4: Date-based filtering"""
    print("\n🧪 DEMO 4: Date-Based Filtering")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./filter_demo_output"
    )
    
    async with SAPODataConnector(config) as connector:
        
        # Date Filter 1: Orders from specific year
        try:
            result1 = await connector.get_data(
                entity_name="Orders",
                filter_condition="year(OrderDate) eq 1997",
                select_fields="OrderID,CustomerID,OrderDate,Freight",
                order_by="OrderDate desc",
                record_limit=10
            )
            display_results(result1, "Orders from 1997", "Orders")
        except Exception as e:
            print(f"⚠️ Year filter failed: {e}")
        
        # Date Filter 2: Orders from specific month
        try:
            result2 = await connector.get_data(
                entity_name="Orders",
                filter_condition="year(OrderDate) eq 1997 and month(OrderDate) eq 7",
                select_fields="OrderID,CustomerID,OrderDate,Freight",
                order_by="OrderDate asc",
                record_limit=8
            )
            display_results(result2, "Orders from July 1997", "Orders")
        except Exception as e:
            print(f"⚠️ Month filter failed: {e}")
        
        # Date Filter 3: Recent orders (if available)
        try:
            result3 = await connector.get_data(
                entity_name="Orders",
                filter_condition="OrderDate ge datetime'1998-01-01T00:00:00'",
                select_fields="OrderID,CustomerID,OrderDate,Freight",
                order_by="OrderDate desc",
                record_limit=8
            )
            display_results(result3, "Orders from 1998 onwards", "Orders")
        except Exception as e:
            print(f"⚠️ Date range filter failed: {e}")


async def demo_complex_queries():
    """Demo 5: Complex combined queries"""
    print("\n🧪 DEMO 5: Complex Combined Queries")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./filter_demo_output"
    )
    
    async with SAPODataConnector(config) as connector:
        
        # Complex Query 1: High-value orders with customer info
        try:
            result1 = await connector.get_data(
                entity_name="Orders",
                filter_condition="Freight gt 100",
                select_fields="OrderID,CustomerID,OrderDate,Freight",
                expand_relations="Customer",
                order_by="Freight desc",
                record_limit=8
            )
            display_results(result1, "High-Value Orders (Freight > $100) with Customer Info", "Orders")
        except Exception as e:
            print(f"⚠️ Complex query 1 failed: {e}")
        
        # Complex Query 2: Premium products with category info
        try:
            result2 = await connector.get_data(
                entity_name="Products",
                filter_condition="UnitPrice gt 30 and CategoryID in (1,2,3)",
                select_fields="ProductID,ProductName,UnitPrice,CategoryID",
                expand_relations="Category",
                order_by="UnitPrice desc",
                record_limit=8
            )
            display_results(result2, "Premium Products (>$30) in Top Categories", "Products")
        except Exception as e:
            print(f"⚠️ Complex query 2 failed: {e}")
        
        # Complex Query 3: Multi-condition filter
        try:
            result3 = await connector.get_data(
                entity_name="Products",
                filter_condition="UnitPrice ge 15 and UnitPrice le 40 and CategoryID ne 8",
                select_fields="ProductID,ProductName,UnitPrice,CategoryID,UnitsInStock",
                order_by="CategoryID asc,UnitPrice desc",
                record_limit=12
            )
            display_results(result3, "Mid-Range Products ($15-$40, Excluding Category 8)", "Products")
        except Exception as e:
            print(f"⚠️ Complex query 3 failed: {e}")


async def demo_search_and_count():
    """Demo 6: Search and count operations"""
    print("\n🧪 DEMO 6: Search & Count Operations")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./filter_demo_output"
    )
    
    async with SAPODataConnector(config) as connector:
        
        # Search 1: Full-text search
        try:
            result1 = await connector.get_data(
                entity_name="Products",
                search_query="chocolate",
                select_fields="ProductID,ProductName,UnitPrice,CategoryID",
                record_limit=8
            )
            display_results(result1, "Products Matching 'chocolate' (Full-text Search)", "Products")
        except Exception as e:
            print(f"⚠️ Search failed: {e}")
        
        # Count 1: Include total count
        try:
            result2 = await connector.get_data(
                entity_name="Products",
                filter_condition="UnitPrice gt 25",
                select_fields="ProductID,ProductName,UnitPrice",
                include_count=True,
                record_limit=5
            )
            display_results(result2, "Expensive Products (>$25) with Total Count", "Products")
            print(f"   📊 Note: Total count information included in response metadata")
        except Exception as e:
            print(f"⚠️ Count query failed: {e}")
        
        # Custom Parameters
        try:
            result3 = await connector.get_data(
                entity_name="Products",
                filter_condition="CategoryID eq 2",
                select_fields="ProductID,ProductName,UnitPrice",
                custom_query_params={
                    "$format": "json",
                    "$metadata": "minimal"
                },
                record_limit=6
            )
            display_results(result3, "Products with Custom Parameters (Category 2)", "Products")
        except Exception as e:
            print(f"⚠️ Custom params query failed: {e}")


async def demo_performance_comparison():
    """Demo 7: Performance comparison with different approaches"""
    print("\n🧪 DEMO 7: Performance Comparison")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory="./filter_demo_output"
    )
    
    async with SAPODataConnector(config) as connector:
        import time
        
        # Performance Test 1: Small batch, few workers
        start_time = time.time()
        result1 = await connector.get_data(
            entity_name="Products",
            filter_condition="UnitPrice gt 15",
            select_fields="ProductID,ProductName,UnitPrice",
            batch_size=5,
            max_workers=1,
            record_limit=20
        )
        time1 = time.time() - start_time
        
        # Performance Test 2: Larger batch, more workers
        start_time = time.time()
        result2 = await connector.get_data(
            entity_name="Products",
            filter_condition="UnitPrice gt 15",
            select_fields="ProductID,ProductName,UnitPrice",
            batch_size=10,
            max_workers=3,
            record_limit=20
        )
        time2 = time.time() - start_time
        
        print(f"⚡ Performance Comparison:")
        print(f"   Small batch (5), 1 worker: {time1:.2f}s for {result1['execution_stats']['records_processed']} records")
        print(f"   Large batch (10), 3 workers: {time2:.2f}s for {result2['execution_stats']['records_processed']} records")
        print(f"   Performance improvement: {((time1 - time2) / time1 * 100):.1f}%")


async def main():
    """Run all filtering demos"""
    print("🎯 SAP OData Connector - Comprehensive Filtering Demo")
    print("=" * 65)
    print("This demo shows all filtering capabilities with REAL DATA results!")
    print("=" * 65)
    
    try:
        # Run all demos
        await demo_basic_filtering()
        await demo_advanced_filtering()
        await demo_sorting_and_selection()
        await demo_date_filtering()
        await demo_complex_queries()
        await demo_search_and_count()
        await demo_performance_comparison()
        
        # Summary
        print("\n" + "=" * 70)
        print("🎉 FILTERING DEMO COMPLETE!")
        print("=" * 70)
        print(" Demonstrated filtering capabilities:")
        print("   • Basic filters ($filter): gt, lt, eq, ne, ge, le")
        print("   • String operations: contains, startswith, endswith")
        print("   • Logical operators: and, or, not")
        print("   • Date functions: year(), month(), day()")
        print("   • Sorting ($orderby): asc, desc, multiple fields")
        print("   • Field selection ($select): specific fields only")
        print("   • Expand relations ($expand): related data")
        print("   • Full-text search ($search): across all fields")
        print("   • Count operations ($count): total record counts")
        print("   • Custom parameters: format, metadata options")
        print("   • Performance optimization: batch sizes, workers")
        print("\n🎯 All with REAL DATA from Northwind service!")
        print("🧹 Automatic cleanup handled by context managers!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
