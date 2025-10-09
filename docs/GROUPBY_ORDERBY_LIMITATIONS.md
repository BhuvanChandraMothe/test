# Group By & Order By Limitations

## ⚠️ Important: OData V2 vs V4 Differences

### The Issue

You're trying to use `group_by` and `aggregate_functions` with an **SAP OData V2 service** (EPM_REF_APPS_SHOP_SRV), but these features require **OData V4's `$apply` system query option**, which is **NOT supported by OData V2**.

---

## What Works vs What Doesn't

### ✅ **Works in Both V2 and V4**

| Feature | OData Parameter | Example | Support |
|---------|----------------|---------|---------|
| **Filter** | `$filter` | `Price gt 100` | ✅ V2 & V4 |
| **Select** | `$select` | `Id,Name,Price` | ✅ V2 & V4 |
| **Expand** | `$expand` | `Supplier,Category` | ✅ V2 & V4 |
| **Order By** | `$orderby` | `Price desc` | ✅ V2 & V4 |
| **Top/Skip** | `$top`, `$skip` | `$top=10&$skip=20` | ✅ V2 & V4 |
| **Search** | `$search` | `electronics` | ⚠️ Limited in V2 |

### ❌ **Only Works in V4**

| Feature | OData Parameter | Example | Support |
|---------|----------------|---------|---------|
| **Group By** | `$apply=groupby(...)` | `groupby((Category))` | ❌ V2, ✅ V4 only |
| **Aggregate** | `$apply=aggregate(...)` | `aggregate(Price with sum)` | ❌ V2, ✅ V4 only |
| **Compute** | `$compute` | `Price mul Quantity as Total` | ❌ V2, ✅ V4 only |

---

## Why Your Test Fails

### Your Code:
```python
await connector.get_data(
    entity_name="Products", 
    group_by="HasReviewOfCurrentUser"  # ❌ This requires OData V4!
)
```

### What Happens:
1. ✅ Connector detects `group_by` parameter
2. ✅ Routes to full pipeline (not lightweight path)
3. ✅ Creates execution plan with group_by
4. ❌ **SAP V2 service rejects the request** because it doesn't support `$apply`

### The Error:
The SAP V2 service returns a **400 Bad Request** when you try to use `$apply` for grouping.

---

## Solutions

### Solution 1: Use OData V4 Service ✅

If you need grouping/aggregation, use an OData V4 service:

```python
# ✅ Works with V4
config = ClientConfig(
    service_url="https://services.odata.org/V4/Northwind/Northwind.svc/",
    output_directory="./v4_data"
)

connector = SAPODataConnector(config)
await connector.initialize()

# This will work with V4
result = await connector.get_data(
    entity_name="Products",
    group_by="CategoryID",
    aggregate_functions="sum(UnitPrice)"
)
```

### Solution 2: Fetch All Data & Group in Python ✅

For V2 services, fetch the data and group it yourself:

```python
# ✅ Fetch all data from V2
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,HasReviewOfCurrentUser"
)

# ✅ Group in Python using pandas
import pandas as pd

# Convert to DataFrame
df = pd.DataFrame([record.data for record in result['data']['Products']['records']])

# Group by in Python
grouped = df.groupby('HasReviewOfCurrentUser').agg({
    'Id': 'count',
    'Name': 'first'
}).rename(columns={'Id': 'Count'})

print(grouped)
```

### Solution 3: Use $orderby (Works in V2) ✅

If you just need sorting (not grouping), use `order_by`:

```python
# ✅ Works with V2
result = await connector.get_data(
    entity_name="Products",
    order_by="HasReviewOfCurrentUser desc, Name asc",  # This works!
    select_fields="Id,Name,HasReviewOfCurrentUser"
)
```

---

## Working Examples

### Example 1: Order By (V2 Compatible) ✅

```python
# Sort products by price descending
result = await connector.get_data(
    entity_name="Products",
    order_by="Price desc",
    limit=10
)
```

### Example 2: Filter + Order By (V2 Compatible) ✅

```python
# Get expensive products, sorted by name
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100",
    order_by="Name asc",
    select_fields="Id,Name,Price"
)
```

### Example 3: Multiple Sort Fields (V2 Compatible) ✅

```python
# Sort by category, then by price
result = await connector.get_data(
    entity_name="Products",
    order_by="Category asc, Price desc"
)
```

### Example 4: Fetch & Group in Python (V2 Compatible) ✅

```python
# Fetch all products
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price,Category"
)

# Group in Python
import pandas as pd
from collections import defaultdict

# Manual grouping
groups = defaultdict(list)
for record in result['data']['Products']['records']:
    category = record.data.get('Category', 'Unknown')
    groups[category].append(record.data)

# Show counts
for category, items in groups.items():
    print(f"{category}: {len(items)} products")
```

### Example 5: Using Pandas for Aggregation (V2 Compatible) ✅

```python
import pandas as pd

# Fetch data
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price,Category"
)

# Convert to DataFrame
records = [record.data for record in result['data']['Products']['records']]
df = pd.DataFrame(records)

# Group and aggregate
summary = df.groupby('Category').agg({
    'Id': 'count',
    'Price': ['mean', 'sum', 'min', 'max']
}).round(2)

print(summary)
```

---

## Quick Reference

### What to Use When

| Your Goal | V2 (SAP) | V4 (Modern) |
|-----------|----------|-------------|
| Sort data | ✅ `order_by="Field desc"` | ✅ `order_by="Field desc"` |
| Filter data | ✅ `filter_condition="Field gt 100"` | ✅ `filter_condition="Field gt 100"` |
| Select fields | ✅ `select_fields="A,B,C"` | ✅ `select_fields="A,B,C"` |
| Expand relations | ✅ `expand_relations="Supplier"` | ✅ `expand_relations="Supplier"` |
| **Group data** | ❌ Fetch + Python grouping | ✅ `group_by="Category"` |
| **Aggregate** | ❌ Fetch + Python aggregation | ✅ `aggregate_functions="sum(Price)"` |

---

## Testing Your Current Setup

### Test 1: Order By (Should Work) ✅

```python
# This should work with your SAP V2 service
await connector.get_data(
    entity_name="Products",
    order_by="Name asc",
    limit=10
)
```

### Test 2: Filter + Order By (Should Work) ✅

```python
# This should work
await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 50",
    order_by="Price desc",
    limit=20
)
```

### Test 3: Group By (Will Fail on V2) ❌

```python
# This will FAIL on SAP V2 service
await connector.get_data(
    entity_name="Products",
    group_by="HasReviewOfCurrentUser"  # ❌ Not supported in V2
)
```

---

## Recommended Approach for Your Use Case

Since you're using **SAP EPM V2 service**, here's what I recommend:

### For Sorting: Use `order_by` ✅

```python
config = ClientConfig(
    sap_server="sapes5.sapdevcenter.com",
    sap_module="ES5",
    username="P2010682507",
    password="Bhuvan@2001",
    output_directory="./demo_output_batch"
)

connector = SAPODataConnector(config)
await connector.initialize()

# ✅ This works!
result = await connector.get_data(
    entity_name="Products",
    order_by="Name asc",  # Sort by name
    select_fields="Id,Name,Price,HasReviewOfCurrentUser"
)
```

### For Grouping: Fetch + Python ✅

```python
# Step 1: Fetch all data
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,HasReviewOfCurrentUser"
)

# Step 2: Group in Python
from collections import Counter

records = [r.data for r in result['data']['Products']['records']]
has_review = [r.get('HasReviewOfCurrentUser') for r in records]
counts = Counter(has_review)

print(f"Products with reviews: {counts[True]}")
print(f"Products without reviews: {counts[False]}")
```

---

## Summary

| Feature | Status | Recommendation |
|---------|--------|----------------|
| `order_by` | ✅ Works in V2 | Use it directly! |
| `filter_condition` | ✅ Works in V2 | Use it directly! |
| `select_fields` | ✅ Works in V2 | Use it directly! |
| `expand_relations` | ✅ Works in V2 | Use it directly! |
| `group_by` | ❌ V4 only | Fetch data + group in Python |
| `aggregate_functions` | ❌ V4 only | Fetch data + aggregate in Python |

---

**Bottom Line**: For SAP V2 services, use `order_by` for sorting, but do grouping/aggregation in Python after fetching the data!
