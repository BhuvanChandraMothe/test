# SAP OData Connector - Feature Reference Guide

Based on your SAP EPM Service Entity Relationships

---

## 📋 Available Entities

From your `entity_relationships.json`:

| Entity | Records | Key Properties | Foreign Keys |
|--------|---------|----------------|--------------|
| **Products** | 123 | Id, Name, Price, StockQuantity | SupplierId → Suppliers |
| **Suppliers** | 45 | Id, Name, Email, Phone | - |
| **Reviews** | 971 | Id, ProductId, Rating, Comment | ProductId → Products |
| **SubCategories** | 26 | Id, Name, MainCategoryId | MainCategoryId → MainCategories |
| **MainCategories** | 6 | Id, Name | - |
| **Images** | 144 | Id, ImageType | - |
| **ReviewAggregates** | 615 | ProductId, AverageRating | ProductId → Products |
| **ShoppingCarts** | 0 | Id, UserId | - |
| **ShoppingCartItems** | 0 | Id, CartId, ProductId | - |

---

## 🎯 Complete Feature Matrix

### Basic Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `entity_name` | str | Single entity to fetch | `"Products"` |
| `selected_entities` | list | Multiple entities | `["Products", "Suppliers"]` |
| `limit` | int | Max records to fetch | `100` |
| `batch_size` | int | Records per request | `500` |
| `max_workers` | int | Parallel workers | `10` |

### Query Options (OData V2 Compatible)

| Parameter | OData Param | Description | Example |
|-----------|-------------|-------------|---------|
| `filter_condition` | `$filter` | Filter records | `"Price gt 100"` |
| `select_fields` | `$select` | Choose fields | `"Id,Name,Price"` |
| `expand_relations` | `$expand` | Include related data | `"Supplier"` |
| `order_by` | `$orderby` | Sort results | `"Price desc"` |

---

## 📖 Examples by Use Case

### 1. Basic Fetching

#### Get All Products
```python
result = await connector.get_data(
    entity_name="Products"
)
```

#### Get Multiple Entities
```python
result = await connector.get_data(
    selected_entities=["Products", "Suppliers", "Reviews"]
)
```

---

### 2. Filtering Examples

#### Simple Comparison
```python
# Products with stock > 50
result = await connector.get_data(
    entity_name="Products",
    filter_condition="StockQuantity gt 50"
)
```

#### Multiple Conditions (AND)
```python
# Products with stock > 30 AND price > 100
result = await connector.get_data(
    entity_name="Products",
    filter_condition="StockQuantity gt 30 and Price gt 100"
)
```

#### Multiple Conditions (OR)
```python
# Products in specific subcategories
result = await connector.get_data(
    entity_name="Products",
    filter_condition="SubCategoryId eq 'Notebooks' or SubCategoryId eq 'Smartphones'"
)
```

#### String Contains
```python
# Products with 'Pro' in name
result = await connector.get_data(
    entity_name="Products",
    filter_condition="substringof('Pro', Name)"
)
```

#### String Starts With
```python
# Products starting with 'Sam'
result = await connector.get_data(
    entity_name="Products",
    filter_condition="startswith(Name, 'Sam')"
)
```

#### Range Filtering
```python
# Products priced between 50 and 200
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price ge 50 and Price le 200"
)
```

#### Boolean Filtering
```python
# Products with reviews from current user
result = await connector.get_data(
    entity_name="Products",
    filter_condition="HasReviewOfCurrentUser eq true"
)
```

#### Date Filtering
```python
# Recent reviews (after Jan 1, 2023)
result = await connector.get_data(
    entity_name="Reviews",
    filter_condition="ChangedAt gt datetime'2023-01-01T00:00:00'"
)
```

---

### 3. Sorting Examples

#### Single Field Sort
```python
# Products sorted by price (descending)
result = await connector.get_data(
    entity_name="Products",
    order_by="Price desc"
)
```

#### Multiple Field Sort
```python
# Sort by category, then by price
result = await connector.get_data(
    entity_name="Products",
    order_by="SubCategoryName asc, Price desc"
)
```

#### Sort with Limit (Top N)
```python
# Get top 10 most expensive products
result = await connector.get_data(
    entity_name="Products",
    order_by="Price desc",
    limit=10
)
```

---

### 4. Field Selection Examples

#### Select Specific Fields
```python
# Get only Id, Name, and Price
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price"
)
```

#### Select with Related Fields
```python
# Include supplier info
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price,Supplier",
    expand_relations="Supplier"
)
```

---

### 5. Expanding Relations

#### Expand Single Relation
```python
# Products with supplier data
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)
```

#### Expand Multiple Relations
```python
# Products with supplier and reviews
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier,Reviews"
)
```

---

### 6. Combined Queries

#### Filter + Sort + Select
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 50",
    order_by="Price desc",
    select_fields="Id,Name,Price,StockQuantity"
)
```

#### Filter + Sort + Select + Expand
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="StockQuantity gt 20",
    order_by="Price desc",
    select_fields="Id,Name,Price,Supplier",
    expand_relations="Supplier",
    limit=10
)
```

---

### 7. Performance Tuning

#### Custom Batch Size
```python
# Smaller batches for memory control
result = await connector.get_data(
    entity_name="Products",
    batch_size=50
)
```

#### More Workers for Speed
```python
# Use 10 parallel workers
result = await connector.get_data(
    selected_entities=["Products", "Suppliers", "Reviews"],
    max_workers=10
)
```

#### Limit Records
```python
# Get only first 100 records
result = await connector.get_data(
    entity_name="Products",
    limit=100
)
```

---

## 🔗 Entity Relationships

Based on your ER diagram:

### Products → Suppliers
```python
# Get products with supplier info
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier",
    select_fields="Id,Name,Price,Supplier"
)
```

### Reviews → Products
```python
# Get reviews with product info
result = await connector.get_data(
    entity_name="Reviews",
    filter_condition="Rating ge 4",
    select_fields="Id,ProductId,Rating,Comment"
)
```

### SubCategories → MainCategories
```python
# Get subcategories with main category
result = await connector.get_data(
    entity_name="SubCategories",
    select_fields="Id,Name,MainCategoryId,MainCategoryName"
)
```

---

## 📊 Filter Operators Reference

### Comparison Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` | Equal | `Price eq 100` |
| `ne` | Not equal | `Price ne 100` |
| `gt` | Greater than | `Price gt 100` |
| `ge` | Greater or equal | `Price ge 100` |
| `lt` | Less than | `Price lt 100` |
| `le` | Less or equal | `Price le 100` |

### Logical Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `and` | Logical AND | `Price gt 50 and Stock lt 100` |
| `or` | Logical OR | `Category eq 'A' or Category eq 'B'` |
| `not` | Logical NOT | `not (Status eq 'Deleted')` |

### String Functions

| Function | Description | Example |
|----------|-------------|---------|
| `substringof(str, field)` | Contains | `substringof('Pro', Name)` |
| `startswith(field, str)` | Starts with | `startswith(Name, 'Sam')` |
| `endswith(field, str)` | Ends with | `endswith(Email, '@sap.com')` |
| `tolower(field)` | To lowercase | `tolower(Name) eq 'product'` |
| `toupper(field)` | To uppercase | `toupper(Code) eq 'ABC'` |

---

## 🎯 Common Use Cases

### Use Case 1: Get Top Selling Products
```python
result = await connector.get_data(
    entity_name="Products",
    order_by="AverageRating desc",
    select_fields="Id,Name,Price,AverageRating",
    limit=10
)
```

### Use Case 2: Get Low Stock Products
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="StockQuantity lt 20",
    order_by="StockQuantity asc",
    select_fields="Id,Name,StockQuantity,Supplier",
    expand_relations="Supplier"
)
```

### Use Case 3: Get Products by Category
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="SubCategoryId eq 'Notebooks'",
    select_fields="Id,Name,Price,SubCategoryName"
)
```

### Use Case 4: Get High-Rated Reviews
```python
result = await connector.get_data(
    entity_name="Reviews",
    filter_condition="Rating ge 4",
    order_by="Rating desc, ChangedAt desc",
    select_fields="Id,ProductId,Rating,Comment,UserDisplayName",
    limit=20
)
```

### Use Case 5: Get All Suppliers with Contact Info
```python
result = await connector.get_data(
    entity_name="Suppliers",
    select_fields="Id,Name,Email,Phone,WebAddress",
    order_by="Name asc"
)
```

---

## 💡 Pro Tips

### Tip 1: Reduce Data Transfer
Always use `select_fields` to get only what you need:
```python
# ❌ Bad - Gets all 20+ fields
result = await connector.get_data(entity_name="Products")

# ✅ Good - Gets only 3 fields
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price"
)
```

### Tip 2: Use Filters Server-Side
Filter on the server, not in Python:
```python
# ❌ Bad - Fetches all, filters in Python
result = await connector.get_data(entity_name="Products")
# Then filter in Python...

# ✅ Good - Filters on server
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

### Tip 3: Combine Filters and Limits
```python
# Get top 10 expensive products with stock
result = await connector.get_data(
    entity_name="Products",
    filter_condition="StockQuantity gt 0",
    order_by="Price desc",
    limit=10
)
```

### Tip 4: Use Batch Size for Large Datasets
```python
# For large datasets, use smaller batches
result = await connector.get_data(
    entity_name="Reviews",  # 971 records
    batch_size=100  # Fetch 100 at a time
)
```

---

## 🚀 Quick Start Template

```python
from covasant_odata.config.models import ClientConfig
from covasant_odata.connector import SAPODataConnector
import asyncio

async def main():
    config = ClientConfig(
        sap_server="sapes5.sapdevcenter.com",
        sap_port=443,
        sap_module="ES5",  
        use_https=True,
        username="P2010682507",
        password="Bhuvan@2001",
        output_directory="./output"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        
        # Your query here
        result = await connector.get_data(
            entity_name="Products",
            filter_condition="Price gt 50",
            order_by="Price desc",
            select_fields="Id,Name,Price",
            limit=10
        )
        
        print(f"Fetched {result['execution_stats']['records_processed']} records")
        
    finally:
        await connector.cleanup()

asyncio.run(main())
```

---

## 📚 Additional Resources

- **Full Demo**: Run `python demo_all_features.py` for complete walkthrough
- **Entity Relationships**: See `entity_relationships.json`
- **CLI Usage**: See `CLI_USAGE_GUIDE.md`
- **OData V2 Spec**: http://www.odata.org/documentation/odata-version-2-0/

---

**Happy Querying! 🎉**
