# Quick Reference - SAP OData Connector

## 🚀 Basic Template

```python
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig
import asyncio

async def main():
    config = ClientConfig(
        service_url="YOUR_SERVICE_URL",
        username="YOUR_USERNAME",
        password="YOUR_PASSWORD",
        output_directory="./output"
    )
    
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # YOUR QUERY HERE
    result = await connector.get_data(entity_name="Products")
    
    await connector.cleanup()

asyncio.run(main())
```

---

## 📋 Parameter Cheat Sheet

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `entity_name` | str | `"Products"` | Single entity to fetch |
| `selected_entities` | list | `["Products", "Orders"]` | Multiple entities |
| `filter_condition` | str | `"Price gt 100"` | OData filter |
| `select_fields` | str | `"ID,Name,Price"` | Fields to return |
| `expand_relations` | str | `"Supplier,Category"` | Relations to join |
| `order_by` | str | `"Price desc"` | Sort order |
| `record_limit` | int | `100` | Max records |
| `batch_size` | int | `500` | Records per page |
| `search_query` | str | `"laptop"` | Full-text search |
| `include_count` | bool | `True` | Include total count |
| `max_workers` | int | `4` | Parallel workers |

---

## 🎯 Common Use Cases

### 1️⃣ Get All Records
```python
result = await connector.get_data(entity_name="Products")
```

### 2️⃣ Filter Records
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

### 3️⃣ Join/Expand Relations
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)
```

### 4️⃣ Multiple Joins
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier,Category,Reviews"
)
```

### 5️⃣ Filter + Join
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100",
    expand_relations="Supplier,Category"
)
```

### 6️⃣ Select Specific Fields
```python
result = await connector.get_data(
    entity_name="Products",
    select_fields="ProductID,Name,Price"
)
```

### 7️⃣ Sort Results
```python
result = await connector.get_data(
    entity_name="Products",
    order_by="Price desc"
)
```

### 8️⃣ Limit Records
```python
result = await connector.get_data(
    entity_name="Products",
    record_limit=50
)
```

### 9️⃣ Everything Combined
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

### 🔟 Multiple Entities
```python
result = await connector.get_data(
    selected_entities=["Products", "Orders", "Customers"],
    batch_size=500
)
```

---

## 🔍 Filter Operators

| Operator | Syntax | Example |
|----------|--------|---------|
| Equal | `eq` | `"Status eq 'Active'"` |
| Not Equal | `ne` | `"Status ne 'Inactive'"` |
| Greater Than | `gt` | `"Price gt 100"` |
| Greater or Equal | `ge` | `"Price ge 100"` |
| Less Than | `lt` | `"Price lt 500"` |
| Less or Equal | `le` | `"Price le 500"` |
| AND | `and` | `"Price gt 100 and Stock gt 0"` |
| OR | `or` | `"Category eq 'A' or Category eq 'B'"` |
| NOT | `not` | `"not (Status eq 'Inactive')"` |

### String Functions
```python
# Starts with
filter_condition="startswith(Name, 'Product')"

# Ends with
filter_condition="endswith(Name, 'Pro')"

# Contains
filter_condition="substringof('laptop', Name)"

# Length
filter_condition="length(Name) gt 10"
```

### Date Functions
```python
# Specific date
filter_condition="OrderDate eq datetime'2024-01-01T00:00:00'"

# Date range
filter_condition="OrderDate ge datetime'2024-01-01T00:00:00' and OrderDate le datetime'2024-12-31T23:59:59'"

# Year
filter_condition="year(OrderDate) eq 2024"

# Month
filter_condition="month(OrderDate) eq 12"
```

---

## 📊 Response Structure

```python
{
    'execution_stats': {
        'duration_seconds': 2.5,
        'records_processed': 124,
        'entities_processed': 1,
        'requests_made': 1,
        'requests_failed': 0,
        'pages_fetched': 1
    },
    'records': [
        {
            'ProductID': '1',
            'Name': 'Laptop',
            'Price': 1200,
            'Supplier': {  # Expanded relation
                'SupplierID': '10',
                'CompanyName': 'Tech Corp'
            }
        }
    ]
}
```

---

## 📁 Output Files

Files are automatically saved with descriptive names:

```
{timestamp}_{entity}_{filters}_{options}.json
```

**Examples:**
- `20251008_125022_products.json`
- `20251008_125020_products_expand_Supplier.json`
- `20251008_125023_products_filter_Price_greater_100_expand_Supplier.json`

---

## ⚡ Performance Tips

| Scenario | Recommendation |
|----------|---------------|
| Small dataset (< 1K) | `batch_size=100-500` |
| Medium dataset (1K-10K) | `batch_size=500-1000` |
| Large dataset (10K-100K) | `batch_size=1000`, use filters |
| Huge dataset (100K+) | Use `record_limit` + filters |
| Testing | Always use `record_limit=10` first |
| Production | Remove `record_limit` |

---

## 🔗 Expand (Join) Patterns

### Single Level
```python
expand_relations="Supplier"
```

### Multiple Relations
```python
expand_relations="Supplier,Category,Reviews"
```

### Nested Relations
```python
expand_relations="Orders/OrderDetails"
```

### Deep Nesting
```python
expand_relations="Orders/OrderDetails/Product/Supplier"
```

### Mixed
```python
expand_relations="Supplier,Orders/OrderDetails"
```

---

## ❌ Common Mistakes

### ❌ Wrong
```python
# Missing await
connector.initialize()

# Wrong filter syntax
filter_condition="Price > 100"  # Should use 'gt'

# Wrong expand syntax
expand_relations=["Supplier", "Category"]  # Should be string

# Forgetting cleanup
await connector.initialize()
result = await connector.get_data(entity_name="Products")
# Missing: await connector.cleanup()
```

### ✅ Correct
```python
# Proper usage
await connector.initialize()

# Correct filter
filter_condition="Price gt 100"

# Correct expand
expand_relations="Supplier,Category"

# Always cleanup
try:
    await connector.initialize()
    result = await connector.get_data(entity_name="Products")
finally:
    await connector.cleanup()
```

---

## 🎨 Mix & Match Examples

### Example 1: E-Commerce
```python
# Active products with full details
result = await connector.get_data(
    entity_name="Products",
    filter_condition="IsActive eq true and Stock gt 0",
    expand_relations="Supplier,Category,Reviews",
    order_by="CreatedDate desc",
    record_limit=100
)
```

### Example 2: Sales Report
```python
# Recent high-value orders
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="OrderDate ge datetime'2024-01-01T00:00:00' and Amount gt 1000",
    expand_relations="Customer,OrderDetails/Product",
    order_by="OrderDate desc"
)
```

### Example 3: Inventory Alert
```python
# Low stock items
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Stock lt 10",
    expand_relations="Supplier",
    select_fields="ProductID,Name,Stock,Supplier",
    order_by="Stock asc"
)
```

### Example 4: Customer Analysis
```python
# US customers with orders
result = await connector.get_data(
    entity_name="Customers",
    filter_condition="Country eq 'USA'",
    expand_relations="Orders",
    order_by="Name asc"
)
```

### Example 5: Bulk Sync
```python
# Sync multiple entities
result = await connector.get_data(
    selected_entities=["Products", "Customers", "Orders"],
    batch_size=1000,
    max_workers=4
)
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid entities requested" | Check entity name spelling |
| "HTTP 401" | Check username/password |
| "HTTP 404" | Check service URL |
| Slow performance | Increase `batch_size` |
| Memory error | Decrease `batch_size` or use `record_limit` |
| No expand data | Check navigation property name |
| Filter not working | Check OData filter syntax |

---

## 📚 See Also

- **USAGE_COMBINATIONS_GUIDE.md** - Detailed combinations guide
- **README.md** - Getting started
- **CONFIGURATION_AND_FILTERING_GUIDE.md** - Advanced filtering

---

**Install**: `pip install covasant_sap_odata_connector`  
**Import**: `from covasant_odata.connector import SAPODataConnector`  
**Version**: 1.0.1
