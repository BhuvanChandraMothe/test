"""
Enhanced SAP OData Connector Test - Demonstrating Advanced Query Capabilities
"""

import asyncio
import os
import shutil
import sys

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig
from odc.query.odata_builder import (
    ODataQueryBuilder, ExpandClause, AggregateClause, 
    AggregateFunction, FilterOperator
)
from odc.monitoring.metrics import get_metrics_collector
from prometheus_client import push_to_gateway


async def test_enhanced_features():
    """Test all enhanced OData query features"""
    
    print("=" * 70)
    print("🚀 ENHANCED SAP ODATA CONNECTOR - ADVANCED FEATURES TEST")
    print("=" * 70)
    
    # Clean up output directory
    output_dir = "./enhanced_test_output"
    if os.path.exists(output_dir):
        print(f"Cleaning up previous test output: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create configuration
    config = ClientConfig(
        service_type="odata",
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=["Products", "Categories", "Orders", "Customers", "Order_Details"],
        output_directory=output_dir
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        print("\n🔧 STEP 1: Initializing connector...")
        await connector.initialize()
        print("✅ Connector initialized successfully!")
        
        # Test 1: Basic Expand Query
        print("\n📊 TEST 1: Products with Category Information (Expand)")
        print("-" * 50)
        
        result1 = await connector.get_data_with_expand(
            entity_name="Products",
            expand_properties=["Category"],
            select_fields=["ProductID", "ProductName", "UnitPrice", "UnitsInStock"],
            filter_condition="UnitPrice gt 20",
            orderby="ProductName asc",
            top=5
        )
        
        print(f"✅ Retrieved {result1['record_count']} products with category info")
        if result1['records']:
            sample = result1['records'][0]
            print(f"   Sample: {sample.get('ProductName')} - ${sample.get('UnitPrice')}")
            if 'Category' in sample:
                print(f"   Category: {sample['Category'].get('CategoryName')}")
        
        # Test 2: Complex Nested Expand
        print("\n📊 TEST 2: Orders with Customer and Order Details (Complex Expand)")
        print("-" * 60)
        
        # Create complex expand clauses
        order_details_expand = ExpandClause(
            property_name="Order_Details",
            select_fields=["ProductID", "Quantity", "UnitPrice"],
            top=3  # Limit order details per order
        )
        
        customer_expand = ExpandClause(
            property_name="Customer",
            select_fields=["CustomerID", "CompanyName", "ContactName", "Country"]
        )
        
        result2 = await connector.get_data_with_expand(
            entity_name="Orders",
            expand_properties=["Customer", "Order_Details"],
            select_fields=["OrderID", "OrderDate", "Freight"],
            filter_condition="Freight gt 50",
            top=3
        )
        
        print(f"✅ Retrieved {result2['record_count']} orders with customer and details")
        if result2['records']:
            sample = result2['records'][0]
            print(f"   Order: {sample.get('OrderID')} - Freight: ${sample.get('Freight')}")
            if 'Customer' in sample:
                print(f"   Customer: {sample['Customer'].get('CompanyName')}")
            if 'Order_Details' in sample:
                print(f"   Order Details: {len(sample['Order_Details'])} items")
        
        # Test 3: Aggregation Query
        print("\n📊 TEST 3: Sales Summary by Category (Aggregation)")
        print("-" * 50)
        
        # Create aggregation clauses
        aggregations = [
            AggregateClause("UnitPrice", AggregateFunction.AVERAGE, "AvgPrice"),
            AggregateClause("UnitsInStock", AggregateFunction.SUM, "TotalStock"),
            AggregateClause("ProductID", AggregateFunction.COUNT, "ProductCount")
        ]
        
        result3 = await connector.get_aggregated_data(
            entity_name="Products",
            group_by_fields=["CategoryID"],
            aggregations=aggregations,
            filter_condition="UnitPrice gt 0"
        )
        
        print(f"✅ Retrieved {result3['record_count']} category summaries")
        if result3['records']:
            for record in result3['records'][:3]:  # Show first 3
                print(f"   Category {record.get('CategoryID')}: "
                      f"Avg Price: ${record.get('AvgPrice', 0):.2f}, "
                      f"Products: {record.get('ProductCount', 0)}")
        
        # Test 4: Custom Query Builder
        print("\n📊 TEST 4: Custom Query with Query Builder")
        print("-" * 45)
        
        # Build a complex custom query
        query_builder = (connector.create_query_builder("Customers")
                        .select("CustomerID", "CompanyName", "ContactName", "Country")
                        .filter_equals("Country", "USA")
                        .filter_contains("CompanyName", "Market")
                        .orderby("CompanyName")
                        .top(10))
        
        result4 = await connector.get_data_with_custom_query(query_builder)
        
        print(f"✅ Retrieved {result4['record_count']} US customers with 'Market' in name")
        if result4['records']:
            for customer in result4['records']:
                print(f"   {customer.get('CompanyName')} - {customer.get('ContactName')}")
        
        # Test 5: Advanced Filtering with Functions
        print("\n📊 TEST 5: Advanced Filtering with OData Functions")
        print("-" * 55)
        
        # Create query with multiple function-based filters
        advanced_query = (connector.create_query_builder("Products")
                         .select("ProductID", "ProductName", "UnitPrice", "CategoryID")
                         .filter("contains(ProductName, 'Cheese')")
                         .filter("UnitPrice ge 10")
                         .orderby("UnitPrice", descending=True)
                         .top(5))
        
        result5 = await connector.get_data_with_custom_query(advanced_query)
        
        print(f"✅ Retrieved {result5['record_count']} cheese products >= $10")
        if result5['records']:
            for product in result5['records']:
                print(f"   {product.get('ProductName')} - ${product.get('UnitPrice')}")
        
        # Test 6: Date Range and Complex Filtering
        print("\n📊 TEST 6: Orders with Date Range and Complex Filters")
        print("-" * 55)
        
        date_query = (connector.create_query_builder("Orders")
                     .select("OrderID", "CustomerID", "OrderDate", "Freight")
                     .filter("OrderDate ge 1996-01-01T00:00:00Z")
                     .filter("OrderDate le 1996-12-31T23:59:59Z")
                     .filter("Freight gt 100")
                     .orderby("Freight", descending=True)
                     .top(10))
        
        result6 = await connector.get_data_with_custom_query(date_query)
        
        print(f"✅ Retrieved {result6['record_count']} high-freight orders from 1996")
        if result6['records']:
            for order in result6['records']:
                print(f"   Order {order.get('OrderID')}: "
                      f"${order.get('Freight')} on {order.get('OrderDate')[:10]}")
        
        # Test 7: Count and Pagination
        print("\n📊 TEST 7: Paginated Results with Count")
        print("-" * 40)
        
        paginated_query = (connector.create_query_builder("Products")
                          .select("ProductID", "ProductName", "UnitPrice")
                          .filter("UnitPrice gt 15")
                          .orderby("UnitPrice", descending=True)
                          .count(True)
                          .skip(5)
                          .top(10))
        
        result7 = await connector.get_data_with_custom_query(paginated_query)
        
        print(f"✅ Retrieved {result7['record_count']} products (page 2)")
        print(f"   Total count: {result7.get('odata_count', 'N/A')}")
        if result7['records']:
            for product in result7['records'][:3]:  # Show first 3
                print(f"   {product.get('ProductName')} - ${product.get('UnitPrice')}")
        
        # Test 8: Multiple Entity Types with Different Queries
        print("\n📊 TEST 8: Multiple Queries in Sequence")
        print("-" * 40)
        
        # Query 1: Top categories by product count
        cat_query = (connector.create_query_builder("Categories")
                    .select("CategoryID", "CategoryName", "Description")
                    .orderby("CategoryName")
                    .top(5))
        
        categories_result = await connector.get_data_with_custom_query(cat_query)
        print(f"✅ Retrieved {categories_result['record_count']} categories")
        
        # Query 2: Suppliers from specific countries
        supplier_query = (connector.create_query_builder("Suppliers")
                         .select("SupplierID", "CompanyName", "Country", "City")
                         .filter_in("Country", ["USA", "UK", "Germany"])
                         .orderby("Country")
                         .orderby("CompanyName")
                         .top(10))
        
        suppliers_result = await connector.get_data_with_custom_query(supplier_query)
        print(f"✅ Retrieved {suppliers_result['record_count']} suppliers from USA/UK/Germany")
        
        # Summary
        print("\n" + "=" * 70)
        print("🎉 ALL ENHANCED FEATURES TESTED SUCCESSFULLY!")
        print("=" * 70)
        
        total_records = (result1['record_count'] + result2['record_count'] + 
                        result3['record_count'] + result4['record_count'] + 
                        result5['record_count'] + result6['record_count'] + 
                        result7['record_count'] + categories_result['record_count'] + 
                        suppliers_result['record_count'])
        
        print(f"📈 Total Records Retrieved: {total_records}")
        print(f"🔍 Query Types Tested: 9")
        print(f"✨ Features Demonstrated:")
        print(f"   • $expand with navigation properties")
        print(f"   • Complex nested $expand operations")
        print(f"   • $apply with groupby and aggregations")
        print(f"   • Advanced $filter with functions")
        print(f"   • $select field projection")
        print(f"   • $orderby sorting")
        print(f"   • $top and $skip pagination")
        print(f"   • $count for total record counts")
        print(f"   • Custom query builder patterns")
        print(f"   • Multiple filter combinations")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        if connector and connector.proxy_pool:
            try:
                await connector._cleanup()
            except:
                pass


async def demonstrate_query_builder_patterns():
    """Demonstrate various query builder patterns"""
    
    print("\n" + "=" * 70)
    print("🔧 QUERY BUILDER PATTERNS DEMONSTRATION")
    print("=" * 70)
    
    # Pattern 1: Simple selection and filtering
    print("\n1️⃣ Simple Selection and Filtering:")
    query1 = (ODataQueryBuilder("Products")
             .select("ProductName", "UnitPrice", "UnitsInStock")
             .filter_equals("CategoryID", 1)
             .filter("UnitPrice gt 20")
             .orderby("ProductName"))
    
    print(f"   Query: {query1}")
    
    # Pattern 2: Complex expand with nested operations
    print("\n2️⃣ Complex Expand with Nested Operations:")
    nested_expand = ExpandClause(
        property_name="Order_Details",
        select_fields=["Quantity", "UnitPrice"],
        filter_condition="Quantity gt 10",
        orderby="Quantity desc",
        top=5
    )
    
    query2 = (ODataQueryBuilder("Orders")
             .select("OrderID", "OrderDate", "Freight")
             .expand(nested_expand)
             .filter_date_range("OrderDate", "1996-01-01T00:00:00Z", "1996-12-31T23:59:59Z")
             .orderby("OrderDate", descending=True))
    
    print(f"   Query: {query2}")
    
    # Pattern 3: Aggregation with grouping
    print("\n3️⃣ Aggregation with Grouping:")
    query3 = (ODataQueryBuilder("Order_Details")
             .groupby("ProductID")
             .sum("Quantity", "TotalQuantity")
             .average("UnitPrice", "AvgPrice")
             .count_distinct("OrderID", "OrderCount")
             .apply_transformation("filter(TotalQuantity gt 100)"))
    
    print(f"   Query: {query3}")
    
    # Pattern 4: Advanced filtering with functions
    print("\n4️⃣ Advanced Filtering with Functions:")
    query4 = (ODataQueryBuilder("Customers")
             .select("CustomerID", "CompanyName", "ContactName")
             .filter("contains(CompanyName, 'Market')")
             .filter("startswith(ContactName, 'A')")
             .filter_in("Country", ["USA", "Canada", "Mexico"])
             .orderby_multiple([("Country", False), ("CompanyName", False)]))
    
    print(f"   Query: {query4}")
    
    # Pattern 5: Pagination with count
    print("\n5️⃣ Pagination with Count:")
    query5 = (ODataQueryBuilder("Products")
             .select("ProductName", "UnitPrice")
             .filter("UnitPrice gt 0")
             .orderby("UnitPrice", descending=True)
             .count(True)
             .skip(20)
             .top(10))
    
    print(f"   Query: {query5}")
    
    print(f"\n✨ All query patterns demonstrated!")


if __name__ == "__main__":
    print("🚀 Starting Enhanced SAP OData Connector Tests...")
    
    # Run query builder pattern demonstration first
    asyncio.run(demonstrate_query_builder_patterns())
    
    # Run main enhanced features test
    success = asyncio.run(test_enhanced_features())
    
    print(f"\n🏁 Test result: {'SUCCESS' if success else 'FAILED'}")
    
    # Force exit to ensure no hanging
    import os
    os._exit(0 if success else 1)
