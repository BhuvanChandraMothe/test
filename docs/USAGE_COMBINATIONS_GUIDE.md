# SAP OData Connector - Complete Usage Combinations Guide

This guide shows all the different ways you can use the `covasant_sap_odata_connector` with various parameter combinations.

## Table of Contents
1. [Basic Usage Patterns](#basic-usage-patterns)
2. [Entity Selection Methods](#entity-selection-methods)
3. [Query Options Combinations](#query-options-combinations)
4. [Performance & Batching](#performance--batching)
5. [Advanced Combinations](#advanced-combinations)
6. [Real-World Examples](#real-world-examples)

---

## Basic Usage Patterns

### 1. Simple Entity Fetch
```python
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig

config = ClientConfig(
    service_url="https://your-sap-server.com/sap/opu/odata/sap/SERVICE/",
    username="your_username",
    password="your_password",
    output_directory="./output"
)

connector = SAPODataConnector(config)
await connector.initialize()

# Fetch all records from one entity
result = await connector.get_data(
    entity_name="Products"
)

await connector.cleanup()
```
**Output File**: `20251008_125022_products.json`

---

## Entity Selection Methods

### Method 1: Single Entity (`entity_name`)
```python
# Fetch one entity - uses lightweight query path
result = await connector.get_data(
    entity_name="Products"
)
```
- ✅ **Fast**: Direct query, no dependency resolution
- ✅ **Simple**: Best for single entity needs
- ✅ **Supports**: All query options ($filter, $expand, $select, etc.)

### Method 2: Multiple Entities (`selected_entities`)
```python
# Fetch multiple entities - uses full pipeline
result = await connector.get_data(
    selected_entities=["Products", "Orders", "Customers"]
)
```
- ✅ **Parallel**: Processes entities in parallel
- ✅ **Smart**: Resolves dependencies automatically
- ✅ **Efficient**: Batch processing with workers

### Method 3: All Entities (no parameters)
```python
# Fetch ALL entities from the service
result = await connector.get_data()
```
- ⚠️ **Caution**: Fetches everything - can be huge!
- ✅ **Complete**: Gets entire dataset

---

## Query Options Combinations

### 1. Filtering (`filter_condition`)

#### Simple Filters
```python
# Equal to
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Category eq 'Electronics'"
)
# File: products_filter_Category_equals_Electronics.json

# Greater than
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
# File: products_filter_Price_greater_100.json

# Less than
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="Amount lt 500"
)
# File: orders_filter_Amount_less_500.json
```

#### Complex Filters
```python
# AND condition
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100 and Category eq 'Electronics'"
)

# OR condition
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Category eq 'Electronics' or Category eq 'Books'"
)

# Date filters
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="OrderDate ge datetime'2024-01-01T00:00:00'"
)

# String functions
result = await connector.get_data(
    entity_name="Customers",
    filter_condition="startswith(Name, 'John')"
)

# Contains
result = await connector.get_data(
    entity_name="Products",
    filter_condition="substringof('laptop', Name)"
)
```

### 2. Field Selection (`select_fields`)

```python
# Select specific fields
result = await connector.get_data(
    entity_name="Products",
    select_fields="ProductID,Name,Price"
)
# File: products_select_3fields.json

# Combine with filter
result = await connector.get_data(
    entity_name="Products",
    select_fields="ProductID,Name,Price,Category",
    filter_condition="Price gt 50"
)
# File: products_filter_Price_greater_50_select_4fields.json
```

### 3. Expanding Relations (`expand_relations`) - JOINS!

#### Single Expand
```python
# Expand one relation
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)
# File: products_expand_Supplier.json
# Each product will have full Supplier data embedded
```

#### Multiple Expands
```python
# Expand multiple relations
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier,Category,Reviews"
)
# File: products_expand_Supplier_Category_Reviews.json
```

#### Nested Expands
```python
# Expand nested relations
result = await connector.get_data(
    entity_name="Orders",
    expand_relations="Customer,OrderDetails/Product"
)
# File: orders_expand_Customer_OrderDetails_Product.json
```

### 4. Ordering (`order_by`)

```python
# Ascending order
result = await connector.get_data(
    entity_name="Products",
    order_by="Price asc"
)
# File: products_order_Price_ascending.json

# Descending order
result = await connector.get_data(
    entity_name="Products",
    order_by="CreatedDate desc"
)
# File: products_order_CreatedDate_descending.json

# Multiple fields
result = await connector.get_data(
    entity_name="Products",
    order_by="Category asc, Price desc"
)
# File: products_order_Category_ascending_Price_descending.json
```

### 5. Search (`search_query`)

```python
# Full-text search (if supported by service)
result = await connector.get_data(
    entity_name="Products",
    search_query="laptop"
)
```

### 6. Count (`include_count`)

```python
# Include total count in response
result = await connector.get_data(
    entity_name="Products",
    include_count=True
)
```

---

## Performance & Batching

### 1. Record Limits

```python
# Limit total records
result = await connector.get_data(
    entity_name="Products",
    record_limit=100
)

# Get first 50 records
result = await connector.get_data(
    entity_name="Products",
    record_limit=50
)
```

### 2. Batch Size (Pagination)

```python
# Small batches (slower, less memory)
result = await connector.get_data(
    entity_name="Products",
    batch_size=50
)

# Large batches (faster, more memory)
result = await connector.get_data(
    entity_name="Products",
    batch_size=1000
)

# Default is 500 - good balance
result = await connector.get_data(
    entity_name="Products"
)
```

### 3. Parallel Processing

```python
# Multiple entities with custom workers
result = await connector.get_data(
    selected_entities=["Products", "Orders", "Customers"],
    batch_size=500,
    max_workers=8  # More parallel workers
)
```

---

## Advanced Combinations

### Combination 1: Filtered Join with Selection
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100",
    expand_relations="Supplier,Category",
    select_fields="ProductID,Name,Price,Supplier,Category",
    order_by="Price desc",
    record_limit=50
)
# File: products_filter_Price_greater_100_select_5fields_order_Price_descending_expand_Supplier_Category.json
```

### Combination 2: Complex Filter with Nested Expand
```python
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="Status eq 'Completed' and TotalAmount gt 1000",
    expand_relations="Customer,OrderDetails/Product/Supplier",
    order_by="OrderDate desc",
    record_limit=100,
    batch_size=25
)
```

### Combination 3: Date Range with Aggregation
```python
result = await connector.get_data(
    entity_name="Sales",
    filter_condition="SaleDate ge datetime'2024-01-01T00:00:00' and SaleDate le datetime'2024-12-31T23:59:59'",
    select_fields="Region,TotalAmount,SaleDate",
    order_by="SaleDate desc"
)
```

### Combination 4: Multiple Entities with Global Limit
```python
result = await connector.get_data(
    selected_entities=["Products", "Suppliers", "Categories"],
    record_limit=1000,  # Total across all entities
    batch_size=300
)
```

---

## Real-World Examples

### Example 1: E-Commerce Product Catalog
```python
# Get active products with supplier and category info
result = await connector.get_data(
    entity_name="Products",
    filter_condition="IsActive eq true and Stock gt 0",
    expand_relations="Supplier,Category,Reviews",
    select_fields="ProductID,Name,Price,Description,Stock,Supplier,Category,Reviews",
    order_by="CreatedDate desc",
    record_limit=500
)
```
**Use Case**: Display products on website with full details

### Example 2: Sales Report
```python
# Get recent high-value orders with customer details
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="OrderDate ge datetime'2024-01-01T00:00:00' and TotalAmount gt 5000",
    expand_relations="Customer,OrderDetails/Product",
    order_by="OrderDate desc",
    batch_size=100
)
```
**Use Case**: Generate sales reports for management

### Example 3: Customer Analysis
```python
# Get customers with their order history
result = await connector.get_data(
    entity_name="Customers",
    filter_condition="Country eq 'USA'",
    expand_relations="Orders,Orders/OrderDetails",
    select_fields="CustomerID,Name,Email,Country,Orders",
    order_by="Name asc"
)
```
**Use Case**: Customer segmentation and analysis

### Example 4: Inventory Check
```python
# Find low-stock products with supplier info
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Stock lt 10 and IsActive eq true",
    expand_relations="Supplier",
    select_fields="ProductID,Name,Stock,ReorderLevel,Supplier",
    order_by="Stock asc"
)
```
**Use Case**: Inventory management and reordering

### Example 5: Full Data Sync
```python
# Sync all master data entities
result = await connector.get_data(
    selected_entities=["Products", "Customers", "Suppliers", "Categories"],
    batch_size=1000,
    max_workers=4
)
```
**Use Case**: Nightly data warehouse sync

### Example 6: Filtered Multi-Entity Fetch
```python
# Get related data with same filter
result = await connector.get_data(
    selected_entities=["Orders", "Invoices", "Shipments"],
    filter_condition="Status eq 'Pending'",
    order_by="CreatedDate desc",
    record_limit=500
)
```
**Use Case**: Dashboard showing pending items across entities

---

## Parameter Compatibility Matrix

| Parameter | Works with `entity_name` | Works with `selected_entities` | Works with no params |
|-----------|-------------------------|-------------------------------|---------------------|
| `filter_condition` | ✅ Yes | ✅ Yes | ✅ Yes |
| `select_fields` | ✅ Yes | ✅ Yes | ✅ Yes |
| `expand_relations` | ✅ Yes | ✅ Yes | ✅ Yes |
| `order_by` | ✅ Yes | ✅ Yes | ✅ Yes |
| `search_query` | ✅ Yes | ✅ Yes | ✅ Yes |
| `include_count` | ✅ Yes | ✅ Yes | ✅ Yes |
| `record_limit` | ✅ Yes | ✅ Yes (global) | ✅ Yes |
| `batch_size` | ✅ Yes | ✅ Yes | ✅ Yes |
| `max_workers` | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Quick Reference: Common Patterns

### Pattern 1: Simple Fetch
```python
result = await connector.get_data(entity_name="Products")
```

### Pattern 2: Filtered Fetch
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

### Pattern 3: Fetch with Join
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)
```

### Pattern 4: Filtered Join
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100",
    expand_relations="Supplier,Category"
)
```

### Pattern 5: Complete Query
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100 and Stock gt 0",
    expand_relations="Supplier,Category",
    select_fields="ProductID,Name,Price,Supplier,Category",
    order_by="Price desc",
    record_limit=100,
    batch_size=50
)
```

### Pattern 6: Multi-Entity Fetch
```python
result = await connector.get_data(
    selected_entities=["Products", "Orders", "Customers"],
    batch_size=500
)
```

---

## Tips & Best Practices

### 🎯 Performance Tips

1. **Use `record_limit`** for testing and development
2. **Increase `batch_size`** for faster bulk operations (500-1000)
3. **Decrease `batch_size`** if you hit memory limits (50-100)
4. **Use `select_fields`** to reduce data transfer
5. **Use `filter_condition`** to fetch only what you need

### 🔗 Join/Expand Tips

1. **Single expand** is fastest: `expand_relations="Supplier"`
2. **Multiple expands** work great: `expand_relations="Supplier,Category"`
3. **Nested expands** for deep relationships: `expand_relations="Orders/OrderDetails/Product"`
4. **Combine with filters** for targeted joins

### 📊 Data Volume Tips

| Records | Recommended `batch_size` | Recommended `record_limit` |
|---------|-------------------------|---------------------------|
| < 1,000 | 100-500 | No limit |
| 1K-10K | 500-1000 | No limit |
| 10K-100K | 1000 | Consider limiting |
| 100K+ | 1000 | Use filters to reduce |

### ⚠️ Common Pitfalls

1. **Don't forget `await connector.initialize()`** before fetching
2. **Always call `await connector.cleanup()`** when done
3. **Test filters with `record_limit`** first
4. **Check field names** - they're case-sensitive
5. **Expand names must match** navigation property names exactly

---

## Output File Naming

The connector automatically names files based on your query:

```
{timestamp}_{entity}_{filter}_{select}_{order}_{expand}.json
```

Examples:
- `20251008_125022_products.json`
- `20251008_125020_products_expand_Supplier.json`
- `20251008_125021_products_expand_Supplier_Reviews.json`
- `20251008_125023_products_filter_Price_greater_100_expand_Supplier.json`

---

## Complete Example: All Features

```python
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def comprehensive_example():
    config = ClientConfig(
        service_url="https://your-sap-server.com/sap/opu/odata/sap/SERVICE/",
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        # Example 1: Simple fetch
        products = await connector.get_data(
            entity_name="Products"
        )
        
        # Example 2: Filtered with join
        active_products = await connector.get_data(
            entity_name="Products",
            filter_condition="IsActive eq true",
            expand_relations="Supplier,Category",
            order_by="CreatedDate desc",
            record_limit=100
        )
        
        # Example 3: Multiple entities
        master_data = await connector.get_data(
            selected_entities=["Products", "Customers", "Suppliers"],
            batch_size=500
        )
        
        # Example 4: Complex query
        sales_report = await connector.get_data(
            entity_name="Orders",
            filter_condition="OrderDate ge datetime'2024-01-01T00:00:00' and Status eq 'Completed'",
            expand_relations="Customer,OrderDetails/Product/Supplier",
            select_fields="OrderID,OrderDate,TotalAmount,Customer,OrderDetails",
            order_by="OrderDate desc",
            batch_size=100
        )
        
        print(f"Products fetched: {products['execution_stats']['records_processed']}")
        print(f"Active products: {active_products['execution_stats']['records_processed']}")
        print(f"Master data records: {master_data['execution_stats']['records_processed']}")
        print(f"Sales records: {sales_report['execution_stats']['records_processed']}")
        
    finally:
        await connector.cleanup()

if __name__ == "__main__":
    asyncio.run(comprehensive_example())
```

---

**Need more help?** Check out:
- `README.md` - Quick start guide
- `CONFIGURATION_AND_FILTERING_GUIDE.md` - Detailed filtering examples
- `UPDATE_PYPI_GUIDE.md` - Package management

**Package**: `covasant_sap_odata_connector` | **Version**: 1.0.1
