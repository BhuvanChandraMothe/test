# SAP OData Connector - Quick Reference Card

## 📦 Installation
```bash
pip install sap-odata-connector-testcov
```

## 🔑 Import (Important!)
```python
from odc.connector import SAPODataConnector  # ✅ Correct
from odc.config.models import ClientConfig
```

## ⚡ Quick Start Template
```python
import asyncio
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def main():
    config = ClientConfig(
        service_url="https://your-server.com/sap/opu/odata/sap/SERVICE/",
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # YOUR QUERIES HERE
    result = await connector.get_data(entity_name="Products")
    
    await connector.cleanup()

asyncio.run(main())
```

## 📋 Common Query Patterns

### 1. Simple Query (All Records)
```python
result = await connector.get_data(entity_name="Products")
```

### 2. With Filter
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

### 3. With JOIN (Expand)
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)
```

### 4. Select Specific Fields
```python
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price"
)
```

### 5. With Sorting
```python
result = await connector.get_data(
    entity_name="Products",
    order_by="Price desc"
)
```

### 6. Limit Results
```python
result = await connector.get_data(
    entity_name="Products",
    record_limit=100
)
```

### 7. Complex Query (All Features)
```python
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="Status eq 'Completed' and Total gt 1000",
    select_fields="Id,OrderDate,Total,CustomerName",
    expand_relations="Customer,OrderDetails",
    order_by="OrderDate desc",
    record_limit=500
)
```

## 🔍 Filter Operators

| Operator | Example |
|----------|---------|
| `eq` | `Status eq 'Active'` |
| `ne` | `Status ne 'Deleted'` |
| `gt` | `Price gt 100` |
| `ge` | `Quantity ge 10` |
| `lt` | `Stock lt 5` |
| `le` | `Discount le 20` |
| `and` | `Price gt 100 and Stock lt 10` |
| `or` | `Category eq 'A' or Category eq 'B'` |
| `contains()` | `contains(Name, 'SAP')` |
| `startswith()` | `startswith(Code, 'PRD')` |

## 📅 Date Filtering
```python
from datetime import datetime, timedelta

# Last 30 days
thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S')
result = await connector.get_data(
    entity_name="Orders",
    filter_condition=f"OrderDate ge datetime'{thirty_days_ago}'"
)
```

## 📊 Access Results
```python
result = await connector.get_data(entity_name="Products")

# Get records
records = result['data']['Products']['records']

# Get stats
stats = result['execution_stats']
print(f"Retrieved {stats['records_processed']} records in {stats['duration_seconds']}s")

# Iterate through records
for record in records:
    print(record.data['Name'], record.data['Price'])
```

## 📁 Output Files
Results auto-saved to:
```
./output/query_results/YYYYMMDD_HHMMSS_entityname_params.json
```

Examples:
- `20251006_161015_products.json`
- `20251006_161023_products_expand_Supplier.json`
- `20251006_161045_orders_filter_Status_equals_Completed.json`

## ⚙️ Configuration Options
```python
config = ClientConfig(
    service_url="...",          # Required
    username="...",             # Required
    password="...",             # Required
    output_directory="./output", # Optional
    use_https=True,             # Optional
    max_workers=10,             # Optional
    timeout=30                  # Optional
)
```

## 🐛 Common Errors

### "No module named 'odc'"
```bash
pip install sap-odata-connector-testcov
```

### "No module named 'odc.utils'"
```bash
pip install sap-odata-connector-testcov --upgrade
```

### Authentication Failed
Check username and password in config

### Empty Results
Test without filter first to verify entity has data

## 💡 Pro Tips

1. **Test with limit first:**
   ```python
   # Test
   test = await connector.get_data(entity_name="Products", record_limit=5)
   # Then fetch all
   full = await connector.get_data(entity_name="Products")
   ```

2. **Use field selection for performance:**
   ```python
   # Faster - only needed fields
   result = await connector.get_data(
       entity_name="Products",
       select_fields="Id,Name,Price"
   )
   ```

3. **Filter on server, not in Python:**
   ```python
   # ✅ Good
   result = await connector.get_data(
       entity_name="Products",
       filter_condition="Price gt 100"
   )
   
   # ❌ Bad
   all_products = await connector.get_data(entity_name="Products")
   filtered = [p for p in all_products if p['Price'] > 100]
   ```

4. **Use expansion instead of multiple queries:**
   ```python
   # ✅ Good - one query
   result = await connector.get_data(
       entity_name="Products",
       expand_relations="Supplier"
   )
   
   # ❌ Bad - multiple queries
   products = await connector.get_data(entity_name="Products")
   for p in products:
       supplier = await connector.get_data(...)
   ```

## 📚 More Help

- **Full Documentation**: See README.md
- **PyPI**: https://pypi.org/project/sap-odata-connector-testcov/
- **Email**: bhuvan.dumpmail@gmail.com

---

**Package**: `sap-odata-connector-testcov` | **Import**: `odc` | **Version**: 1.0.0
