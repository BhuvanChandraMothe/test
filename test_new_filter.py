import asyncio
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def simple_demo():
    
    print("Simple SAP OData Connector Demo")
    print("=" * 50)
    
    # Step 1: Configure the connector
    config = ClientConfig(
        # service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        # username="P2010682507",
        # password="Bhuvan@2001",
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        sap_module="ES5",  # Automatically mapped to EPM_REF_APPS_SHOP_SRV
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./demo_output_multi"  #log this to the user so that he can see where the files are being saved.
    )
    
    # Step 2: Create connector instance
    connector = SAPODataConnector(config)
    
    try:
        # Step 3: Initialize
        await connector.initialize()
        print("Connector initialized successfully!")
        print("-" * 50)
        
        # SAP EPM SHOP SERVICE TESTING
        
        # Test 1: Get all Products - logs are automatic!
        # print("\nFetching Products...")
        products = await connector.get_data(selected_entities=["Products","Reviews"])
        # print(f"Done! Retrieved {products['execution_stats']['records_processed']} products")
        
        # Test 2: Get all Reviews - logs are automatic!
        # print("\nFetching Reviews...")
        # reviews = await connector.get_data(entity_name="Reviews")
        # print(f"Done! Retrieved {reviews['execution_stats']['records_processed']} reviews")
        
        # # Test 2: Get all Reviews (largest dataset)
        # print("Getting all reviews...")
        # reviews = await connector.get_data(entity_name="Reviews")
        # print(f"Retrieved {reviews['execution_stats']['records_processed']} reviews")
        
        # # Test 3: Get Suppliers
        # print("Getting all suppliers...")
        # suppliers = await connector.get_data(entity_name="Suppliers")
        # print(f"Retrieved {suppliers['execution_stats']['records_processed']} suppliers")
        
        
        # from datetime import datetime, timedelta
        # six_months_ago = datetime.now() - timedelta(days=180)
        # six_months_ago_str = six_months_ago.strftime('%Y-%m-%dT%H:%M:%S')
        
        # last6m_data = await connector.get_data(
        #     entity_name="Reviews",
        #     filter_condition=f"ChangedAt ge datetime'{six_months_ago_str}'",
        #     select_fields="Id,Rating,Comment,ChangedAt,ProductId",
        #     order_by="ChangedAt desc",
        #     record_limit=30
        # )
        
        
        
        #joning data
        # supXprod = await connector.get_data(
        #     entity_name="Products",
        #     expand_relations="Supplier",
        # )
            
        
        # datetime'YYYY-MM-DDTHH:MM:SS'
        # oct_data = await connector.get_data(
        #     entity_name="Reviews",
        #     filter_condition="month(ChangedAt) eq 10 and year(ChangedAt) eq 2023",
        #     select_fields="Id,Rating,Comment,ChangedAt,ProductId",
        #     order_by="ChangedAt desc"
        # )
        
        
        
        # # Products by category (Beverages = CategoryID 1)
        # print("Getting beverages (CategoryID = 1)...")
        # beverages = await connector.get_data(
        #     entity_name="Products",
        #     filter_condition="CategoryID eq 1"
        # )
        # print(f"Retrieved {beverages['execution_stats']['records_processed']} beverages")
        
        # # Discontinued products
        # print("Getting discontinued products...")
        # discontinued = await connector.get_data(
        #     entity_name="Products",
        #     filter_condition="Discontinued eq true"
        # )
        # print(f"Retrieved {discontinued['execution_stats']['records_processed']} discontinued products")
        
        # # Products with low stock (UnitsInStock < 10)
        # print("Getting low stock products (UnitsInStock < 10)...")
        # low_stock = await connector.get_data(
        #     entity_name="Products",
        #     filter_condition="UnitsInStock lt 10"
        # )
        # print(f"Retrieved {low_stock['execution_stats']['records_processed']} low stock products")
        
        # # CUSTOMERS TABLE FILTERING
        # print("\n--- CUSTOMERS TABLE FILTERING ---")
        
        # # German customers
        # print("Getting German customers...")
        # german_customers = await connector.get_data(
        #     entity_name="Customers",
        #     filter_condition="Country eq 'Germany'"
        # )
        # print(f"Retrieved {german_customers['execution_stats']['records_processed']} German customers")
        
        # # Customers from specific cities
        # print("Getting customers from London or Berlin...")
        # city_customers = await connector.get_data(
        #     entity_name="Customers",
        #     filter_condition="City eq 'London' or City eq 'Berlin'"
        # )
        # print(f"Retrieved {city_customers['execution_stats']['records_processed']} customers from London or Berlin")
        
        # # Customers with specific contact titles
        # print("Getting customers with 'Owner' in contact title...")
        # owner_customers = await connector.get_data(
        #     entity_name="Customers",
        #     filter_condition="contains(ContactTitle, 'Owner')"
        # )
        # print(f"Retrieved {owner_customers['execution_stats']['records_processed']} customers with 'Owner' title")
        
        # # ORDERS TABLE FILTERING
        # print("\n--- ORDERS TABLE FILTERING ---")
        
        # # Recent orders (OrderDate > 1997-01-01)
        # print("Getting orders from 1997...")
        # recent_orders = await connector.get_data(
        #     entity_name="Orders",
        #     filter_condition="year(OrderDate) eq 1997"
        # )
        # print(f"Retrieved {recent_orders['execution_stats']['records_processed']} orders from 1997")
        
        # # High freight orders (Freight > 50)
        # print("Getting high freight orders (Freight > 50)...")
        # high_freight = await connector.get_data(
        #     entity_name="Orders",
        #     filter_condition="Freight gt 50"
        # )
        # print(f"Retrieved {high_freight['execution_stats']['records_processed']} high freight orders")
        
        # # Orders shipped to specific countries
        # print("Getting orders shipped to USA or UK...")
        # country_orders = await connector.get_data(
        #     entity_name="Orders",
        #     filter_condition="ShipCountry eq 'USA' or ShipCountry eq 'UK'"
        # )
        # print(f"Retrieved {country_orders['execution_stats']['records_processed']} orders to USA or UK")
        
        # # EMPLOYEES TABLE FILTERING
        # print("\n--- EMPLOYEES TABLE FILTERING ---")
        
        # # Employees from specific cities
        # print("Getting employees from Seattle...")
        # seattle_employees = await connector.get_data(
        #     entity_name="Employees",
        #     filter_condition="City eq 'Seattle'"
        # )
        # print(f"Retrieved {seattle_employees['execution_stats']['records_processed']} employees from Seattle")
        
        # # Employees hired after specific date
        # print("Getting employees hired after 1993...")
        # new_employees = await connector.get_data(
        #     entity_name="Employees",
        #     filter_condition="year(HireDate) gt 1993"
        # )
        # print(f"Retrieved {new_employees['execution_stats']['records_processed']} employees hired after 1993")
        
        # # SUPPLIERS TABLE FILTERING
        # print("\n--- SUPPLIERS TABLE FILTERING ---")
        
        # # Suppliers from specific countries
        # print("Getting suppliers from USA...")
        # usa_suppliers = await connector.get_data(
        #     entity_name="Suppliers",
        #     filter_condition="Country eq 'USA'"
        # )
        # print(f"Retrieved {usa_suppliers['execution_stats']['records_processed']} USA suppliers")
        
        # # Suppliers from specific regions
        # print("Getting suppliers from specific regions...")
        # region_suppliers = await connector.get_data(
        #     entity_name="Suppliers",
        #     filter_condition="Region ne null"
        # )
        # print(f"Retrieved {region_suppliers['execution_stats']['records_processed']} suppliers with region data")
        
        # # CATEGORIES TABLE FILTERING
        # print("\n--- CATEGORIES TABLE FILTERING ---")
        
        # # All categories
        # print("Getting all categories...")
        # categories = await connector.get_data(entity_name="Categories")
        # print(f"Retrieved {categories['execution_stats']['records_processed']} categories")
        
        # # Categories with specific names
        # print("Getting categories containing 'Dairy'...")
        # dairy_categories = await connector.get_data(
        #     entity_name="Categories",
        #     filter_condition="contains(CategoryName, 'Dairy')"
        # )
        # print(f"Retrieved {dairy_categories['execution_stats']['records_processed']} dairy categories")
        
        # # ORDER DETAILS TABLE FILTERING
        # print("\n--- ORDER DETAILS TABLE FILTERING ---")
        
        # # High quantity order details (Quantity > 50)
        # print("Getting order details with high quantity (> 50)...")
        # high_quantity = await connector.get_data(
        #     entity_name="Order_Details",
        #     filter_condition="Quantity gt 50"
        # )
        # print(f"Retrieved {high_quantity['execution_stats']['records_processed']} high quantity order details")
        
        # # Order details with discount
        # print("Getting order details with discount...")
        # discounted = await connector.get_data(
        #     entity_name="Order_Details",
        #     filter_condition="Discount gt 0"
        # )
        # print(f"Retrieved {discounted['execution_stats']['records_processed']} discounted order details")
        
        # # ADVANCED FILTERING WITH SORTING AND FIELD SELECTION
        # print("\n--- ADVANCED FILTERING EXAMPLES ---")
        
        # # Top 5 most expensive products with specific fields
        # print("Getting top 5 most expensive products...")
        # top_expensive = await connector.get_data(
        #     entity_name="Products",
        #     select_fields="ProductID,ProductName,UnitPrice,CategoryID",
        #     order_by="UnitPrice desc"
        # )
        # print(f"Retrieved {top_expensive['execution_stats']['records_processed']} products sorted by price")
        
        # # Customers sorted by company name with specific fields
        # print("Getting customers sorted by company name...")
        # sorted_customers = await connector.get_data(
        #     entity_name="Customers",
        #     select_fields="CustomerID,CompanyName,City,Country",
        #     order_by="CompanyName asc"
        # )
        # print(f"Retrieved {sorted_customers['execution_stats']['records_processed']} customers sorted by name")
        
        # # Orders with count
        # print("Getting orders with total count...")
        # orders_with_count = await connector.get_data(
        #     entity_name="Orders",
        #     select_fields="OrderID,CustomerID,OrderDate,Freight",
        #     include_count=True
        # )
        # print(f"Retrieved {orders_with_count['execution_stats']['records_processed']} orders with count")
        
        # # COMPLEX FILTER CONDITIONS
        # print("\n--- COMPLEX FILTER CONDITIONS ---")
        
        # # Products with multiple conditions
        # print("Getting products: price between 10-30 AND not discontinued...")
        # complex_products = await connector.get_data(
        #     entity_name="Products",
        #     filter_condition="UnitPrice ge 10 and UnitPrice le 30 and Discontinued eq false"
        # )
        # print(f"Retrieved {complex_products['execution_stats']['records_processed']} products matching complex criteria")
        
        # # Orders with date range and freight conditions
        # print("Getting orders: from 1997 with freight > 20...")
        # complex_orders = await connector.get_data(
        #     entity_name="Orders",
        #     filter_condition="year(OrderDate) eq 1997 and Freight gt 20"
        # )
        # print(f"Retrieved {complex_orders['execution_stats']['records_processed']} orders matching date and freight criteria")
        
        
        
    except Exception as e:
        print(f"FAILED: Error: {e}")
    
    finally:
        # Step 8: Cleanup
        await connector.cleanup()


if __name__ == "__main__":
    print("Starting Simple Demo...")
    asyncio.run(simple_demo())
    print("Test is done!")
