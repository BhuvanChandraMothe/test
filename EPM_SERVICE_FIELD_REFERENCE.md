# EPM Service Field Reference

## ⚠️ Important: Field Names are Case-Sensitive!

The SAP EPM_REF_APPS_SHOP_SRV service uses **different field names** than standard OData conventions.

---

## Products Entity - Available Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `Id` | String | **Product ID** (NOT `ProductID`) |
| `Name` | String | Product name |
| `Description` | String | Product description |
| `Price` | Decimal | Product price |
| `CurrencyCode` | String | Currency (e.g., "EUR", "USD") |
| `StockQuantity` | Integer | Available stock |
| `QuantityUnit` | String | Unit of measure |
| `AverageRating` | Decimal | Average customer rating |
| `RatingCount` | Integer | Number of ratings |
| `ImageUrl` | String | Product image URL |
| `SupplierId` | String | Supplier ID |
| `SupplierName` | String | Supplier name |
| `MainCategoryId` | String | Main category ID |
| `MainCategoryName` | String | Main category name |
| `SubCategoryId` | String | Sub-category ID |
| `SubCategoryName` | String | Sub-category name |
| `DimensionWidth` | Decimal | Product width |
| `DimensionDepth` | Decimal | Product depth |
| `DimensionHeight` | Decimal | Product height |
| `DimensionUnit` | String | Dimension unit |
| `WeightMeasure` | Decimal | Product weight |
| `WeightUnit` | String | Weight unit |
| `MeasureUnit` | String | Measure unit |
| `LastModified` | DateTime | Last modification date |
| `IsFavoriteOfCurrentUser` | Boolean | Is favorite flag |
| `HasReviewOfCurrentUser` | Boolean | Has review flag |

### Navigation Properties (for `expand_relations`)

| Navigation Property | Target Entity | Description |
|---------------------|---------------|-------------|
| `Supplier` | Supplier | Product supplier |
| `SubCategory` | Category | Product sub-category |
| `Reviews` | Review | Product reviews |
| `Images` | ProductImage | Product images |
| `ReviewAggregates` | ReviewAggregate | Review aggregates |

---

## Common Mistakes vs Correct Usage

### ❌ Wrong (Standard OData Names)
```python
result = await connector.get_data(
    entity_name="Products",
    select_fields="ProductID,ProductName,Category",  # WRONG!
    expand_relations="Category"  # WRONG!
)
```

### ✅ Correct (EPM Service Names)
```python
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,SubCategoryName",  # CORRECT!
    expand_relations="SubCategory"  # CORRECT!
)
```

---

## Working Examples for EPM Service

### Example 1: Basic Product Query
```python
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price,CurrencyCode",
    filter_condition="Price gt 100",
    order_by="Price desc",
    record_limit=50
)
```
**File**: `products_filter_Price_greater_100_select_4fields_order_Price_descending.json`

### Example 2: Products with Supplier
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier",
    select_fields="Id,Name,Price,Supplier",
    filter_condition="StockQuantity gt 0",
    record_limit=50
)
```
**File**: `products_filter_StockQuantity_greater_0_select_4fields_expand_Supplier.json`

### Example 3: Products with Category and Supplier
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier,SubCategory",
    select_fields="Id,Name,Price,Supplier,SubCategory",
    filter_condition="Price gt 100",
    order_by="Price desc",
    record_limit=50
)
```
**File**: `products_filter_Price_greater_100_select_5fields_order_Price_descending_expand_Supplier_SubCategory.json`

### Example 4: Products with Reviews
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Reviews,Supplier",
    select_fields="Id,Name,AverageRating,RatingCount,Reviews,Supplier",
    filter_condition="RatingCount gt 5",
    order_by="AverageRating desc"
)
```

### Example 5: Search by Name
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="substringof('Notebook', Name)",
    select_fields="Id,Name,Price,Description",
    order_by="Price asc"
)
```

### Example 6: Filter by Category
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="MainCategoryName eq 'Computer Systems'",
    expand_relations="Supplier,SubCategory",
    order_by="Name asc"
)
```

### Example 7: Low Stock Alert
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="StockQuantity lt 10 and StockQuantity gt 0",
    expand_relations="Supplier",
    select_fields="Id,Name,StockQuantity,Supplier",
    order_by="StockQuantity asc"
)
```

---

## Other Entities in EPM Service

### Suppliers
- Fields: `Id`, `Name`, `EmailAddress`, `PhoneNumber`, `Street`, `City`, `PostalCode`, `Country`
- Navigation: `Products`

### Reviews
- Fields: `Id`, `ProductId`, `UserId`, `Rating`, `Comment`, `CreatedAt`
- Navigation: `Product`

### MainCategories
- Fields: `Id`, `Name`
- Navigation: `SubCategories`

### SubCategories  
- Fields: `Id`, `Name`, `MainCategoryId`
- Navigation: `MainCategory`, `Products`

---

## Quick Field Mapping Reference

| You Want | EPM Field Name |
|----------|----------------|
| Product ID | `Id` |
| Product Name | `Name` |
| Category | `SubCategory` or `MainCategoryName` |
| Category ID | `SubCategoryId` or `MainCategoryId` |
| Supplier | `Supplier` (navigation) |
| Supplier Name | `SupplierName` |
| Stock | `StockQuantity` |
| Rating | `AverageRating` |
| Review Count | `RatingCount` |

---

## How to Find Field Names for Any Service

### Method 1: Fetch One Record
```python
result = await connector.get_data(
    entity_name="Products",
    record_limit=1
)
# Check the saved JSON file to see all field names
```

### Method 2: Check Service Metadata
Visit: `https://your-service-url/$metadata`

Example: `https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/$metadata`

### Method 3: Use SAP Gateway Client
- Transaction: `/IWFND/GW_CLIENT`
- Execute GET request
- Inspect response structure

---

## Tips

1. **Always test with `record_limit=1`** first to see field names
2. **Field names are case-sensitive** - `Id` ≠ `ID` ≠ `id`
3. **Navigation properties** must match exactly for `expand_relations`
4. **Check the saved JSON file** to see the actual structure
5. **Use `select_fields`** to reduce data transfer and improve performance

---

## Error Messages

### "Resource not found for the segment 'ProductID'"
❌ **Problem**: Wrong field name  
✅ **Solution**: Use `Id` instead of `ProductID`

### "Resource not found for the segment 'Category'"
❌ **Problem**: Wrong navigation property  
✅ **Solution**: Use `SubCategory` instead of `Category`

### "The property 'ProductName' does not exist"
❌ **Problem**: Wrong field name  
✅ **Solution**: Use `Name` instead of `ProductName`

---

**Service URL**: `https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/`  
**Metadata**: `https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/$metadata`
