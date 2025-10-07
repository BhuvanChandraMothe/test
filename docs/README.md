# SAP OData Connector (TestCov Edition)

[![PyPI version](https://badge.fury.io/py/sap-odata-connector-testcov.svg)](https://pypi.org/project/sap-odata-connector-testcov/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful, enterprise-grade Python library for seamlessly connecting to SAP OData services. Built for data engineers, analysts, and developers who need reliable, high-performance data extraction from SAP systems with minimal code.

**Stop writing boilerplate code for SAP data extraction. Start building data pipelines in minutes.**

---

## 🎯 Why Use This Library?

### The Problem
Extracting data from SAP OData services typically requires:
- ❌ Manual pagination handling (SAP limits responses to 500 records)
- ❌ Complex authentication setup
- ❌ Handling relationship expansions manually
- ❌ Writing repetitive filtering and query logic
- ❌ Managing connection pooling and retries
- ❌ Parsing and transforming OData responses

### The Solution
This library handles all of that for you:
- ✅ **Automatic Pagination**: Fetches all records automatically, no matter the size
- ✅ **Smart Relationship Expansion**: JOIN-like queries with `$expand`
- ✅ **Advanced Filtering**: Full OData query support with simple syntax
- ✅ **Auto-Save Results**: Query results saved with unique, descriptive filenames
- ✅ **Production-Ready**: Built-in retry logic, connection pooling, and error handling
- ✅ **Clean Logging**: Professional execution summaries without clutter

---

## 📦 Installation

```bash
pip install sap-odata-connector-testcov
```

### Requirements
- Python 3.8 or higher
- SAP OData service credentials

### Important Note on Imports

The package name is `sap-odata-connector-testcov`, but you import it as `odc`:

```python
# ✅ Correct
from odc.connector import SAPODataConnector

# ❌ Wrong - hyphens can't be used in Python imports
from sap-odata-connector-testcov import *
```

### 📚 Complete Documentation

- **[Configuration & Filtering Guide](CONFIGURATION_AND_FILTERING_GUIDE.md)** - Complete reference for all configuration options and filter syntax
- **[Quick Reference](QUICK_REFERENCE.md)** - One-page cheat sheet
- **[User Guide](USER_GUIDE.md)** - Detailed user guide

---

## 🚀 Quick Start (30 Seconds)

```python
import asyncio
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def main():
    # 1. Configure
    config = ClientConfig(
        service_url="https://your-sap-server.com/sap/opu/odata/sap/SERVICE_NAME/",
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    # 2. Connect
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # 3. Query - That's it!
    result = await connector.get_data(entity_name="Products")
    print(f"✅ Retrieved {result['execution_stats']['records_processed']} products")
    
    # 4. Cleanup
    await connector.cleanup()

asyncio.run(main())
```

**Output:**
```
✅ Retrieved 2,547 products in 4.2 seconds
📁 Results saved to: ./output/query_results/20251006_161015_products.json
```

---

## 🎓 Complete Feature Guide

### 1. Basic Data Extraction

#### Fetch All Records from an Entity

```python
# Automatically handles pagination - fetches ALL records
result = await connector.get_data(entity_name="Products")

# Access the data
products = result['data']['Products']['records']
print(f"Total records: {len(products)}")
```

**What happens behind the scenes:**
- Automatically paginates through all pages (500 records per page)
- Handles OData V2 and V4 formats
- Saves results to JSON file with timestamp
- Provides detailed execution stats

---

### 2. Advanced Filtering

#### Simple Filters

```python
# Products with price greater than 100
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)

# Orders with specific status
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="Status eq 'Completed'"
)

# Customers from Germany
result = await connector.get_data(
    entity_name="Customers",
    filter_condition="Country eq 'Germany'"
)
```

#### Complex Filters with Multiple Conditions

```python
# Combine multiple conditions with 'and' / 'or'
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100 and Category eq 'Electronics'"
)

# Date-based filtering
from datetime import datetime, timedelta

six_months_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%dT%H:%M:%S')
result = await connector.get_data(
    entity_name="Orders",
    filter_condition=f"OrderDate ge datetime'{six_months_ago}'"
)

# String operations
result = await connector.get_data(
    entity_name="Customers",
    filter_condition="contains(CompanyName, 'Tech')"
)
```

#### OData Filter Operators Reference

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `Status eq 'Active'` |
| `ne` | Not equal | `Status ne 'Inactive'` |
| `gt` | Greater than | `Price gt 100` |
| `ge` | Greater or equal | `Quantity ge 10` |
| `lt` | Less than | `Stock lt 5` |
| `le` | Less or equal | `Discount le 20` |
| `and` | Logical AND | `Price gt 100 and Stock lt 10` |
| `or` | Logical OR | `Category eq 'A' or Category eq 'B'` |
| `not` | Logical NOT | `not (Status eq 'Deleted')` |
| `contains()` | String contains | `contains(Name, 'SAP')` |
| `startswith()` | String starts with | `startswith(Code, 'PRD')` |
| `endswith()` | String ends with | `endswith(Email, '@company.com')` |

---

### 3. Relationship Expansion (JOINs)

One of the most powerful features - fetch related data in a single query!

#### Single Relationship Expansion

```python
# Get Products WITH their Supplier information
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)

# Each product now includes full supplier details
for record in result['data']['Products']['records']:
    product_name = record.data['Name']
    supplier_name = record.data['Supplier']['CompanyName']
    print(f"{product_name} from {supplier_name}")
```

#### Multiple Relationship Expansions

```python
# Get Orders with Customer AND OrderDetails
result = await connector.get_data(
    entity_name="Orders",
    expand_relations="Customer,OrderDetails"
)

# Get Products with Category AND Supplier
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Category,Supplier"
)
```

#### Nested Expansions

```python
# Get Orders with OrderDetails, and expand Product within OrderDetails
result = await connector.get_data(
    entity_name="Orders",
    expand_relations="OrderDetails/Product"
)
```

**Real-world example:**
```python
# Complete order information with all related data
result = await connector.get_data(
    entity_name="Orders",
    expand_relations="Customer,OrderDetails/Product,ShippingAddress"
)

# Now you have:
# - Order details
# - Customer information
# - All order line items
# - Product details for each line item
# - Shipping address
# All in ONE query!
```

---

### 4. Field Selection (Performance Optimization)

Only fetch the fields you need - reduces data transfer and improves performance.

```python
# Get only specific fields
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price,Category"
)

# Combine with filtering
result = await connector.get_data(
    entity_name="Customers",
    select_fields="Id,CompanyName,Country,Email",
    filter_condition="Country eq 'USA'"
)

# With expansion - select fields from related entities too
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price",
    expand_relations="Supplier",
    filter_condition="Price gt 50"
)
```

---

### 5. Sorting and Ordering

```python
# Sort by single field (ascending)
result = await connector.get_data(
    entity_name="Products",
    order_by="Price asc"
)

# Sort descending
result = await connector.get_data(
    entity_name="Orders",
    order_by="OrderDate desc"
)

# Sort by multiple fields
result = await connector.get_data(
    entity_name="Products",
    order_by="Category asc, Price desc"
)
```

---

### 6. Limiting Results

```python
# Get only top 100 records
result = await connector.get_data(
    entity_name="Products",
    record_limit=100
)

# Top 50 most expensive products
result = await connector.get_data(
    entity_name="Products",
    order_by="Price desc",
    record_limit=50
)
```

---

### 7. Combining Multiple Features

The real power comes from combining features:

```python
# Complex business query example
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="OrderDate ge datetime'2024-01-01T00:00:00' and Status eq 'Shipped'",
    select_fields="Id,OrderDate,TotalAmount,CustomerName",
    expand_relations="Customer,OrderDetails/Product",
    order_by="OrderDate desc",
    record_limit=1000
)
```

**This single query:**
- ✅ Filters orders from 2024 that are shipped
- ✅ Selects only needed fields
- ✅ Expands customer and product details
- ✅ Sorts by date (newest first)
- ✅ Limits to 1000 records
- ✅ Handles pagination automatically
- ✅ Saves results with descriptive filename

---

## 📊 Output Files

All query results are automatically saved with unique, descriptive filenames:

```
./output/query_results/
├── 20251006_161015_products.json
├── 20251006_161023_products_expand_Supplier.json
├── 20251006_161045_orders_filter_Status_equals_Completed.json
├── 20251006_161102_customers_select_5fields_order_CompanyName_ascending.json
└── 20251006_161215_products_filter_Price_greater_100_expand_Category.json
```

### File Naming Convention

Files are named based on query parameters:
- Timestamp: `YYYYMMDD_HHMMSS`
- Entity name: `products`, `orders`, etc.
- Filter: `filter_Price_greater_100`
- Expansion: `expand_Supplier`
- Selection: `select_5fields`
- Ordering: `order_Price_descending`

### File Contents

```json
{
  "query_info": {
    "entity_name": "Products",
    "filter_condition": "Price gt 100",
    "select_fields": "Id,Name,Price",
    "expand_relations": "Supplier",
    "total_records": 247,
    "timestamp": "2025-10-06T16:10:15",
    "filename": "20251006_161015_products_filter_Price_greater_100_expand_Supplier.json"
  },
  "data": [
    {
      "Id": "P001",
      "Name": "Product A",
      "Price": 150.00,
      "Supplier": {
        "CompanyName": "Supplier Inc",
        "Country": "USA"
      }
    }
    // ... more records
  ]
}
```

---

## 🎯 Real-World Use Cases

### Use Case 1: Data Migration

```python
# Extract all customer data for migration
async def migrate_customers():
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # Get all customers with addresses
    customers = await connector.get_data(
        entity_name="Customers",
        expand_relations="Addresses,ContactPersons"
    )
    
    # Data is automatically saved and ready for migration
    print(f"Extracted {customers['execution_stats']['records_processed']} customers")
    await connector.cleanup()
```

### Use Case 2: Business Intelligence / Reporting

```python
# Monthly sales report
async def monthly_sales_report():
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # Get this month's orders with full details
    from datetime import datetime
    month_start = datetime.now().replace(day=1).strftime('%Y-%m-%dT00:00:00')
    
    orders = await connector.get_data(
        entity_name="Orders",
        filter_condition=f"OrderDate ge datetime'{month_start}'",
        expand_relations="Customer,OrderDetails/Product",
        order_by="OrderDate desc"
    )
    
    # Analyze the data
    total_revenue = sum(order.data['TotalAmount'] for order in orders['data']['Orders']['records'])
    print(f"Monthly Revenue: ${total_revenue:,.2f}")
    
    await connector.cleanup()
```

### Use Case 3: Data Synchronization

```python
# Sync products updated in last 24 hours
async def sync_recent_products():
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
    
    products = await connector.get_data(
        entity_name="Products",
        filter_condition=f"ModifiedDate ge datetime'{yesterday}'",
        expand_relations="Category,Supplier"
    )
    
    print(f"Found {products['execution_stats']['records_processed']} updated products")
    # Process and sync to your database
    
    await connector.cleanup()
```

### Use Case 4: Data Quality Analysis

```python
# Find incomplete customer records
async def find_incomplete_customers():
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # Get customers missing email or phone
    customers = await connector.get_data(
        entity_name="Customers",
        filter_condition="Email eq null or Phone eq null",
        select_fields="Id,CompanyName,Email,Phone,Country"
    )
    
    print(f"Found {customers['execution_stats']['records_processed']} incomplete records")
    await connector.cleanup()
```

### Use Case 5: ETL Pipeline

```python
# Complete ETL pipeline
async def etl_pipeline():
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # Extract
    print("Extracting data...")
    products = await connector.get_data(
        entity_name="Products",
        expand_relations="Category,Supplier",
        filter_condition="Active eq true"
    )
    
    # Transform (your custom logic)
    print("Transforming data...")
    transformed_data = transform_products(products['data']['Products']['records'])
    
    # Load (to your destination)
    print("Loading data...")
    load_to_database(transformed_data)
    
    print(f"✅ ETL Complete: {len(transformed_data)} products processed")
    await connector.cleanup()
```

---

## 🔧 Advanced Configuration

### Full Configuration Options

```python
config = ClientConfig(
    # Required
    service_url="https://your-sap-server.com/sap/opu/odata/sap/SERVICE_NAME/",
    username="your_username",
    password="your_password",
    
    # Optional
    output_directory="./output",           # Where to save results
    use_https=True,                        # Use HTTPS (recommended)
    max_workers=10,                        # Concurrent workers
    batch_size=100,                        # Batch processing size
    total_records_limit=None,              # Global record limit (None = unlimited)
    timeout=30,                            # Request timeout in seconds
)
```

### Using with Context Manager

```python
async def query_data():
    config = ClientConfig(...)
    
    async with SAPODataConnector(config) as connector:
        # Connector is automatically initialized and cleaned up
        result = await connector.get_data(entity_name="Products")
        return result
```

### Error Handling

```python
async def safe_query():
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        result = await connector.get_data(entity_name="Products")
        
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except ValueError as e:
        print(f"Invalid query: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        await connector.cleanup()
```

---

## 📈 Performance Tips

### 1. Use Field Selection
```python
# ❌ Slow - fetches all fields
result = await connector.get_data(entity_name="Products")

# ✅ Fast - fetches only needed fields
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price"
)
```

### 2. Use Filters to Reduce Data
```python
# ❌ Fetches everything then filters in Python
all_products = await connector.get_data(entity_name="Products")
expensive = [p for p in all_products if p['Price'] > 100]

# ✅ Filters on server - much faster
expensive = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

### 3. Use Record Limits for Testing
```python
# During development, limit records
result = await connector.get_data(
    entity_name="Products",
    record_limit=10  # Just get 10 for testing
)
```

### 4. Batch Processing for Large Datasets
```python
# For very large datasets, process in batches
async def process_large_dataset():
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    batch_size = 1000
    skip = 0
    
    while True:
        result = await connector.get_data(
            entity_name="Products",
            record_limit=batch_size
        )
        
        if not result['data']['Products']['records']:
            break
            
        # Process this batch
        process_batch(result['data']['Products']['records'])
        skip += batch_size
    
    await connector.cleanup()
```

---

## 🔍 Logging and Monitoring

The connector provides detailed execution logs:

```
15:19:54 - odc.connector - INFO - START: Querying for Products with automatic pagination
15:19:54 - odc.connector - INFO - Paginated query completed: 2547 records in 4.23s (6 requests)
15:19:54 - odc.connector - INFO - Detailed stats: Requests made: 6, Total records: 2547, Duration: 4.23s
15:19:54 - odc.connector - INFO - Query results saved to: ./output/query_results/20251006_151954_products.json
```

### Execution Statistics

Every query returns detailed stats:

```python
result = await connector.get_data(entity_name="Products")

stats = result['execution_stats']
print(f"Duration: {stats['duration_seconds']} seconds")
print(f"Records: {stats['records_processed']}")
print(f"Requests: {stats['requests_made']}")
print(f"Pages: {stats['pages_fetched']}")
```

---

## 🧪 Testing Your Queries

### Test with Small Limits First

```python
# Test your query with a small limit first
test_result = await connector.get_data(
    entity_name="Products",
    filter_condition="Category eq 'Electronics'",
    record_limit=5  # Just 5 records for testing
)

# Check if it works
if test_result['execution_stats']['records_processed'] > 0:
    print("✅ Query works! Now fetch all:")
    
    # Remove limit to fetch all
    full_result = await connector.get_data(
        entity_name="Products",
        filter_condition="Category eq 'Electronics'"
    )
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. "No module named 'odc'"

**Problem**: Package not installed

**Solution**:
```bash
pip install sap-odata-connector-testcov
```

#### 2. "No module named 'odc.utils'"

**Problem**: Old version installed

**Solution**:
```bash
pip uninstall sap-odata-connector-testcov
pip install sap-odata-connector-testcov --upgrade
```

#### 3. Authentication Errors

**Problem**: Invalid credentials

**Solution**: Check your username and password:
```python
config = ClientConfig(
    service_url="...",
    username="correct_username",  # Verify this
    password="correct_password"   # Verify this
)
```

#### 4. Connection Timeout

**Problem**: Server not responding

**Solution**: Increase timeout:
```python
config = ClientConfig(
    service_url="...",
    timeout=60  # Increase from default 30 seconds
)
```

#### 5. Empty Results

**Problem**: Filter too restrictive or entity is empty

**Solution**: Test without filter first:
```python
# Test without filter
result = await connector.get_data(entity_name="Products")

if result['execution_stats']['records_processed'] == 0:
    print("Entity is empty")
else:
    print(f"Entity has {result['execution_stats']['records_processed']} records")
    # Now try with filter
```

---

## 📚 API Reference

### Main Methods

#### `get_data()`

Main method for querying data.

```python
result = await connector.get_data(
    entity_name: str,                    # Required: Entity to query
    filter_condition: str = None,        # OData filter expression
    select_fields: str = None,           # Comma-separated field list
    expand_relations: str = None,        # Comma-separated relations to expand
    order_by: str = None,                # OData orderby expression
    search_query: str = None,            # OData search query
    record_limit: int = None,            # Maximum records to fetch
    include_count: bool = False,         # Include total count
    custom_query_params: dict = None     # Custom OData parameters
)
```

**Returns**: Dictionary with:
- `execution_stats`: Query execution statistics
- `data`: Query results organized by entity

### Configuration

#### `ClientConfig`

```python
from odc.config.models import ClientConfig

config = ClientConfig(
    service_url: str,              # SAP OData service URL
    username: str,                 # SAP username
    password: str,                 # SAP password
    output_directory: str = "./output",
    use_https: bool = True,
    max_workers: int = 10,
    batch_size: int = 100,
    total_records_limit: int = None,
    timeout: int = 30
)
```

---

## 🌟 Best Practices

### 1. Always Use Try-Finally for Cleanup

```python
connector = SAPODataConnector(config)
try:
    await connector.initialize()
    result = await connector.get_data(entity_name="Products")
finally:
    await connector.cleanup()  # Always cleanup
```

### 2. Use Specific Field Selection

```python
# ✅ Good - only fetch what you need
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price"
)

# ❌ Bad - fetches all fields (slower)
result = await connector.get_data(entity_name="Products")
```

### 3. Filter on the Server, Not in Python

```python
# ✅ Good - filter on SAP server
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)

# ❌ Bad - fetch everything then filter
all_products = await connector.get_data(entity_name="Products")
filtered = [p for p in all_products if p['Price'] > 100]
```

### 4. Use Expansion Instead of Multiple Queries

```python
# ✅ Good - one query with expansion
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier,Category"
)

# ❌ Bad - multiple queries
products = await connector.get_data(entity_name="Products")
for product in products:
    supplier = await connector.get_data(entity_name="Suppliers", filter_condition=f"Id eq '{product.SupplierId}'")
```

### 5. Test Queries with Limits First

```python
# ✅ Good - test with small limit
test = await connector.get_data(entity_name="Products", record_limit=10)
# Verify it works, then fetch all
full = await connector.get_data(entity_name="Products")
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 👨‍💻 Author

**Bhuvan Chandra Mothe**
- Email: bhuvan.dumpmail@gmail.com
- GitHub: https://github.com

---

## 🆘 Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Email: bhuvan.dumpmail@gmail.com

---

## 📝 Changelog

### Version 1.0.0 (2025-10-06)
- ✅ Initial release
- ✅ Core OData querying functionality
- ✅ Automatic pagination support
- ✅ Relationship expansion ($expand)
- ✅ Advanced filtering and ordering
- ✅ Automatic file saving with unique names
- ✅ Clean professional logging
- ✅ BigQuery integration support
- ✅ 100+ dependencies bundled
- ✅ Production-ready error handling

---

## 🎓 Learn More

### OData Resources
- [OData Protocol](https://www.odata.org/)
- [SAP OData Documentation](https://help.sap.com/docs/odata)

### Python Async Resources
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [aiohttp Documentation](https://docs.aiohttp.org/)

---

**Made with ❤️ for the SAP data community**

**Happy Data Extracting! 🚀**
