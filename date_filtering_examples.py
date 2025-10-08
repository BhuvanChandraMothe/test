"""
Date-based filtering examples for SAP OData Connector
Shows how to filter data between specific date ranges
"""

import asyncio
from datetime import datetime
from covasant_odata.config.models import ClientConfig
from covasant_odata.connector import SAPODataConnector


async def date_filtering_examples():
    """Examples of date-based filtering"""
    
    print("DATE FILTERING EXAMPLES")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./date_filter_output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        print("SUCCESS: Connector initialized")
        
        # Example 1: Products modified between 2001-2020
        print("\n1. PRODUCTS MODIFIED BETWEEN 2001-2020")
        print("-" * 50)
        
        result1 = await connector.get_data(
            entity_name="Products",
            filter_condition="LastModified ge datetime'2001-01-01T00:00:00' and LastModified le datetime'2020-01-01T00:00:00'",
            select_fields="Id,Name,LastModified,Price,AverageRating",
            order_by="LastModified desc",
            record_limit=20
        )
        
        count1 = result1['execution_stats']['records_processed']
        print(f"RESULTS: Found {count1} products modified between 2001-2020")
        
        # Example 2: Reviews created between specific dates
        print("\n2. REVIEWS CREATED BETWEEN 2020-2024")
        print("-" * 50)
        
        result2 = await connector.get_data(
            entity_name="Reviews",
            filter_condition="ChangedAt ge datetime'2020-01-01T00:00:00' and ChangedAt le datetime'2024-12-31T23:59:59'",
            select_fields="Id,Rating,Comment,ChangedAt,ProductId,UserDisplayName",
            order_by="ChangedAt desc",
            record_limit=50
        )
        
        count2 = result2['execution_stats']['records_processed']
        print(f"RESULTS: Found {count2} reviews created between 2020-2024")
        
        # Example 3: Products modified in specific year
        print("\n3. PRODUCTS MODIFIED IN 2023")
        print("-" * 50)
        
        result3 = await connector.get_data(
            entity_name="Products",
            filter_condition="year(LastModified) eq 2023",
            select_fields="Id,Name,LastModified,Price",
            order_by="LastModified desc"
        )
        
        count3 = result3['execution_stats']['records_processed']
        print(f"RESULTS: Found {count3} products modified in 2023")
        
        # Example 4: Reviews from last 6 months (relative date)
        print("\n4. REVIEWS FROM RECENT PERIOD")
        print("-" * 50)
        
        # Calculate 6 months ago from today
        from datetime import datetime, timedelta
        six_months_ago = datetime.now() - timedelta(days=180)
        six_months_ago_str = six_months_ago.strftime('%Y-%m-%dT%H:%M:%S')
        
        result4 = await connector.get_data(
            entity_name="Reviews",
            filter_condition=f"ChangedAt ge datetime'{six_months_ago_str}'",
            select_fields="Id,Rating,Comment,ChangedAt,ProductId",
            order_by="ChangedAt desc",
            record_limit=30
        )
        
        count4 = result4['execution_stats']['records_processed']
        print(f"RESULTS: Found {count4} reviews from last 6 months")
        
        # Example 5: Products modified in specific month/year
        print("\n5. PRODUCTS MODIFIED IN JANUARY 2024")
        print("-" * 50)
        
        result5 = await connector.get_data(
            entity_name="Products",
            filter_condition="year(LastModified) eq 2024 and month(LastModified) eq 1",
            select_fields="Id,Name,LastModified,Price,StockQuantity",
            order_by="LastModified desc"
        )
        
        count5 = result5['execution_stats']['records_processed']
        print(f"RESULTS: Found {count5} products modified in January 2024")
        
        # Example 6: Combine date filter with other conditions
        print("\n6. HIGH-RATED PRODUCTS MODIFIED RECENTLY")
        print("-" * 50)
        
        result6 = await connector.get_data(
            entity_name="Products",
            filter_condition="LastModified ge datetime'2023-01-01T00:00:00' and AverageRating ge 4.0 and Price gt 100",
            select_fields="Id,Name,LastModified,Price,AverageRating,StockQuantity",
            order_by="AverageRating desc, LastModified desc",
            record_limit=15
        )
        
        count6 = result6['execution_stats']['records_processed']
        print(f"RESULTS: Found {count6} high-rated expensive products modified since 2023")
        
        # Summary
        print("\n" + "=" * 60)
        print("DATE FILTERING SUMMARY")
        print("=" * 60)
        print(f"Products 2001-2020: {count1} records")
        print(f"Reviews 2020-2024: {count2} records")
        print(f"Products in 2023: {count3} records")
        print(f"Recent reviews: {count4} records")
        print(f"Products Jan 2024: {count5} records")
        print(f"High-rated recent products: {count6} records")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await connector.cleanup()
            print("\nCLEANUP: Completed")
        except:
            pass


async def advanced_date_patterns():
    """Advanced date filtering patterns"""
    
    print("\n" + "=" * 60)
    print("ADVANCED DATE FILTERING PATTERNS")
    print("=" * 60)
    
    config = ClientConfig(
        service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./advanced_date_output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        # Pattern 1: Weekend reviews (Saturday/Sunday)
        print("\n1. REVIEWS CREATED ON WEEKENDS")
        print("-" * 40)
        
        # Note: OData may not have direct weekday function, but we can try
        result1 = await connector.get_data(
            entity_name="Reviews",
            filter_condition="ChangedAt ge datetime'2024-01-01T00:00:00'",
            select_fields="Id,Rating,ChangedAt,UserDisplayName",
            order_by="ChangedAt desc",
            record_limit=20
        )
        
        print(f"RESULTS: Found {result1['execution_stats']['records_processed']} recent reviews")
        
        # Pattern 2: Business hours filter (9 AM to 5 PM)
        print("\n2. REVIEWS CREATED DURING BUSINESS HOURS")
        print("-" * 40)
        
        result2 = await connector.get_data(
            entity_name="Reviews",
            filter_condition="hour(ChangedAt) ge 9 and hour(ChangedAt) le 17",
            select_fields="Id,Rating,ChangedAt,Comment",
            record_limit=25
        )
        
        print(f"RESULTS: Found {result2['execution_stats']['records_processed']} reviews during business hours")
        
        # Pattern 3: Quarterly analysis
        print("\n3. PRODUCTS MODIFIED IN Q1 2024")
        print("-" * 40)
        
        result3 = await connector.get_data(
            entity_name="Products",
            filter_condition="LastModified ge datetime'2024-01-01T00:00:00' and LastModified le datetime'2024-03-31T23:59:59'",
            select_fields="Id,Name,LastModified,Price",
            order_by="LastModified desc"
        )
        
        print(f"RESULTS: Found {result3['execution_stats']['records_processed']} products modified in Q1 2024")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    finally:
        try:
            await connector.cleanup()
        except:
            pass


if __name__ == "__main__":
    print("STARTING DATE FILTERING EXAMPLES...")
    
    # Run basic date filtering examples
    success1 = asyncio.run(date_filtering_examples())
    
    if success1:
        # Run advanced patterns
        success2 = asyncio.run(advanced_date_patterns())
        
        if success2:
            print("\nSUCCESS: All date filtering examples completed!")
            print("\nCheck the output directories for saved data files:")
            print("  • ./date_filter_output/query_results/")
            print("  • ./advanced_date_output/query_results/")
        else:
            print("\nWARNING: Some advanced examples failed")
    else:
        print("\nERROR: Basic examples failed")
    
    print("\nDATE FILTERING GUIDE:")
    print("Use these patterns in your filter_condition parameter!")
