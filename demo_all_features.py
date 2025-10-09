"""
COMPLETE WALKTHROUGH: All get_data() Features
Using SAP EPM Service with Entity Relationships

This demonstrates:
- Basic fetching
- Filtering ($filter)
- Sorting ($orderby)
- Field selection ($select)
- Expanding relations ($expand)
- Limiting records
- Batch sizes
- Multiple entities
- Complex queries
"""
from covasant_odata.config.models import ClientConfig
from covasant_odata.connector import SAPODataConnector
import asyncio


async def demo_all_features():
    """Complete demonstration of all get_data() capabilities"""
    
    # Configuration
    config = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        sap_module="ES5",  
        use_https=True,
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./demo_all_features_output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        print("\n" + "="*80)
        print("SAP ODATA CONNECTOR - COMPLETE FEATURE WALKTHROUGH")
        print("="*80)
        
        await connector.initialize()
        
        # ====================================================================
        # DEMO 1: Basic Fetch - Get all records from an entity
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 1: Basic Fetch - Get All Products")
        print("="*80)
        
        result1 = await connector.get_data(
            entity_name="Products"
        )
        
        print(f"✅ Fetched {result1['execution_stats']['records_processed']} products")
        print(f"   Duration: {result1['execution_stats']['duration_seconds']:.2f}s")
        print(f"   Output: {config.output_directory}/processed/Products/")
        
        # ====================================================================
        # DEMO 2: Filtering - Get products with specific criteria
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 2: Filtering - Products with Stock > 50")
        print("="*80)
        print("Filter: StockQuantity gt 50")
        
        result2 = await connector.get_data(
            entity_name="Products",
            filter_condition="StockQuantity gt 50"
        )
        
        print(f"✅ Fetched {result2['execution_stats']['records_processed']} products with stock > 50")
        print(f"   Duration: {result2['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 3: Multiple Filter Conditions
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 3: Complex Filtering - Products with Stock > 30 AND Price > 100")
        print("="*80)
        print("Filter: StockQuantity gt 30 and Price gt 100")
        
        result3 = await connector.get_data(
            entity_name="Products",
            filter_condition="StockQuantity gt 30 and Price gt 100"
        )
        
        print(f"✅ Fetched {result3['execution_stats']['records_processed']} products")
        print(f"   Duration: {result3['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 4: String Filtering
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 4: String Filtering - Products containing 'Pro' in name")
        print("="*80)
        print("Filter: substringof('Pro', Name)")
        
        result4 = await connector.get_data(
            entity_name="Products",
            filter_condition="substringof('Pro', Name)"
        )
        
        print(f"✅ Fetched {result4['execution_stats']['records_processed']} products")
        print(f"   Duration: {result4['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 5: Sorting - Order by field
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 5: Sorting - Products sorted by Price (descending)")
        print("="*80)
        print("OrderBy: Price desc")
        
        result5 = await connector.get_data(
            entity_name="Products",
            order_by="Price desc",
            limit=10  # Get top 10 most expensive
        )
        
        print(f"✅ Fetched {result5['execution_stats']['records_processed']} products (top 10 by price)")
        print(f"   Duration: {result5['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 6: Multiple Sort Fields
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 6: Multi-field Sorting - By SubCategory (asc), then Price (desc)")
        print("="*80)
        print("OrderBy: SubCategoryName asc, Price desc")
        
        result6 = await connector.get_data(
            entity_name="Products",
            order_by="SubCategoryName asc, Price desc",
            limit=20
        )
        
        print(f"✅ Fetched {result6['execution_stats']['records_processed']} products")
        print(f"   Duration: {result6['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 7: Field Selection - Get only specific fields
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 7: Field Selection - Get only Id, Name, Price")
        print("="*80)
        print("Select: Id,Name,Price")
        
        result7 = await connector.get_data(
            entity_name="Products",
            select_fields="Id,Name,Price",
            limit=15
        )
        
        print(f"✅ Fetched {result7['execution_stats']['records_processed']} products (3 fields only)")
        print(f"   Duration: {result7['execution_stats']['duration_seconds']:.2f}s")
        print(f"   Reduced data transfer by selecting only needed fields!")
        
        # ====================================================================
        # DEMO 8: Expand Relations - Get related data
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 8: Expand Relations - Products with Supplier data")
        print("="*80)
        print("Expand: Supplier")
        
        result8 = await connector.get_data(
            entity_name="Products",
            expand_relations="Supplier",
            select_fields="Id,Name,Price,Supplier",
            limit=10
        )
        
        print(f"✅ Fetched {result8['execution_stats']['records_processed']} products with supplier info")
        print(f"   Duration: {result8['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 9: Combining Multiple Options
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 9: Combined Query - Filter + Sort + Select + Expand")
        print("="*80)
        print("Filter: Price gt 50")
        print("OrderBy: Price desc")
        print("Select: Id,Name,Price,StockQuantity,Supplier")
        print("Expand: Supplier")
        
        result9 = await connector.get_data(
            entity_name="Products",
            filter_condition="Price gt 50",
            order_by="Price desc",
            select_fields="Id,Name,Price,StockQuantity,Supplier",
            expand_relations="Supplier",
            limit=10
        )
        
        print(f"✅ Fetched {result9['execution_stats']['records_processed']} products")
        print(f"   Duration: {result9['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 10: Limiting Records
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 10: Record Limiting - Get only first 5 products")
        print("="*80)
        
        result10 = await connector.get_data(
            entity_name="Products",
            limit=5
        )
        
        print(f"✅ Fetched {result10['execution_stats']['records_processed']} products (limited to 5)")
        print(f"   Duration: {result10['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 11: Batch Size Control
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 11: Batch Size - Fetch with custom batch size")
        print("="*80)
        print("Batch Size: 20 records per request")
        
        result11 = await connector.get_data(
            entity_name="Products",
            batch_size=20,
            limit=50
        )
        
        print(f"✅ Fetched {result11['execution_stats']['records_processed']} products")
        print(f"   Duration: {result11['execution_stats']['duration_seconds']:.2f}s")
        print(f"   Used smaller batches for controlled data transfer")
        
        # ====================================================================
        # DEMO 12: Different Entity - Suppliers
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 12: Different Entity - Fetch All Suppliers")
        print("="*80)
        
        result12 = await connector.get_data(
            entity_name="Suppliers",
            select_fields="Id,Name,Email,Phone"
        )
        
        print(f"✅ Fetched {result12['execution_stats']['records_processed']} suppliers")
        print(f"   Duration: {result12['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 13: Reviews with Filtering
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 13: Reviews - High ratings only (Rating >= 4)")
        print("="*80)
        print("Filter: Rating ge 4")
        
        result13 = await connector.get_data(
            entity_name="Reviews",
            filter_condition="Rating ge 4",
            select_fields="Id,ProductId,Rating,Comment,UserDisplayName",
            order_by="Rating desc",
            limit=20
        )
        
        print(f"✅ Fetched {result13['execution_stats']['records_processed']} high-rated reviews")
        print(f"   Duration: {result13['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 14: SubCategories with Parent Reference
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 14: SubCategories - With MainCategory filter")
        print("="*80)
        print("Filter: MainCategoryId eq 'Electronics'")
        
        result14 = await connector.get_data(
            entity_name="SubCategories",
            filter_condition="MainCategoryId eq 'Electronics'",
            select_fields="Id,Name,MainCategoryName"
        )
        
        print(f"✅ Fetched {result14['execution_stats']['records_processed']} electronics subcategories")
        print(f"   Duration: {result14['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 15: Multiple Entities at Once
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 15: Multiple Entities - Fetch Products, Suppliers, and Reviews")
        print("="*80)
        
        result15 = await connector.get_data(
            selected_entities=["Products", "Suppliers", "Reviews"]
        )
        
        print(f"✅ Fetched data from {result15['execution_stats']['entities_processed']} entities")
        print(f"   Total records: {result15['execution_stats']['records_processed']}")
        print(f"   Duration: {result15['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 16: Date Filtering (for Reviews)
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 16: Date Filtering - Recent reviews")
        print("="*80)
        print("Filter: ChangedAt gt datetime'2023-01-01T00:00:00'")
        
        result16 = await connector.get_data(
            entity_name="Reviews",
            filter_condition="ChangedAt gt datetime'2023-01-01T00:00:00'",
            order_by="ChangedAt desc",
            limit=10
        )
        
        print(f"✅ Fetched {result16['execution_stats']['records_processed']} recent reviews")
        print(f"   Duration: {result16['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 17: Boolean Filtering
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 17: Boolean Filtering - Products with reviews from current user")
        print("="*80)
        print("Filter: HasReviewOfCurrentUser eq true")
        
        result17 = await connector.get_data(
            entity_name="Products",
            filter_condition="HasReviewOfCurrentUser eq true",
            select_fields="Id,Name,AverageRating"
        )
        
        print(f"✅ Fetched {result17['execution_stats']['records_processed']} products")
        print(f"   Duration: {result17['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 18: OR Conditions
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 18: OR Filtering - Products in specific subcategories")
        print("="*80)
        print("Filter: SubCategoryId eq 'Notebooks' or SubCategoryId eq 'Smartphones'")
        
        result18 = await connector.get_data(
            entity_name="Products",
            filter_condition="SubCategoryId eq 'Notebooks' or SubCategoryId eq 'Smartphones'",
            select_fields="Id,Name,SubCategoryName,Price"
        )
        
        print(f"✅ Fetched {result18['execution_stats']['records_processed']} products")
        print(f"   Duration: {result18['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 19: Numeric Range Filtering
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 19: Range Filtering - Products priced between 50 and 200")
        print("="*80)
        print("Filter: Price ge 50 and Price le 200")
        
        result19 = await connector.get_data(
            entity_name="Products",
            filter_condition="Price ge 50 and Price le 200",
            select_fields="Id,Name,Price",
            order_by="Price asc"
        )
        
        print(f"✅ Fetched {result19['execution_stats']['records_processed']} products in price range")
        print(f"   Duration: {result19['execution_stats']['duration_seconds']:.2f}s")
        
        # ====================================================================
        # DEMO 20: Performance Tuning - Max Workers
        # ====================================================================
        print("\n" + "="*80)
        print("DEMO 20: Performance Tuning - Using more workers")
        print("="*80)
        print("Max Workers: 10 (parallel processing)")
        
        result20 = await connector.get_data(
            selected_entities=["Products", "Suppliers", "SubCategories"],
            max_workers=10
        )
        
        print(f"✅ Fetched data from {result20['execution_stats']['entities_processed']} entities")
        print(f"   Total records: {result20['execution_stats']['records_processed']}")
        print(f"   Duration: {result20['execution_stats']['duration_seconds']:.2f}s")
        print(f"   Used parallel processing for faster execution!")
        
        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("\n" + "="*80)
        print("WALKTHROUGH COMPLETE!")
        print("="*80)
        print("\n📊 Summary of Demonstrated Features:")
        print("  ✅ Basic fetching")
        print("  ✅ Filtering (simple, complex, string, date, boolean, range)")
        print("  ✅ Sorting (single field, multiple fields)")
        print("  ✅ Field selection ($select)")
        print("  ✅ Expanding relations ($expand)")
        print("  ✅ Record limiting")
        print("  ✅ Batch size control")
        print("  ✅ Multiple entities")
        print("  ✅ Performance tuning")
        print("\n📁 All results saved to:", config.output_directory)
        print("\n🎓 Key Takeaways:")
        print("  • Use filter_condition for WHERE clauses")
        print("  • Use order_by for sorting")
        print("  • Use select_fields to reduce data transfer")
        print("  • Use expand_relations to get related data")
        print("  • Use limit to control record count")
        print("  • Use batch_size for memory management")
        print("  • Use max_workers for parallel processing")
        
    finally:
        await connector.cleanup()


if __name__ == "__main__":
    asyncio.run(demo_all_features())
