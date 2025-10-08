# SAP OData Connector - Complete Configuration & Filtering Guide

## 📋 Table of Contents
1. [Configuration Options](#configuration-options)
2. [Connection Methods](#connection-methods)
3. [SAP Module Mapping](#sap-module-mapping)
4. [Filtering Guide](#filtering-guide)
5. [Query Options](#query-options)
6. [Advanced Examples](#advanced-examples)

---

## 🔧 Configuration Options

### Complete ClientConfig Parameters

```python
from covasant_odata.config.models import ClientConfig

config = ClientConfig(
    # ========== CONNECTION METHOD 1: Using SAP Module (Recommended) ==========
    sap_server="sapes5.sapdevcenter.com",    # SAP server hostname/IP
    sap_port=443,                             # Port (default: 8000, HTTPS: 443)
    sap_module="ES5",                         # SAP module name (auto-maps to service)
    use_https=True,                           # Use HTTPS (default: True)
    
    # ========== CONNECTION METHOD 2: Using Service Name Directly ==========
    # sap_server="sapes5.sapdevcenter.com",
    # sap_port=443,
    # service_name="EPM_REF_APPS_SHOP_SRV",  # Direct OData service name
    # use_https=True,
    
    # ========== CONNECTION METHOD 3: Using Full URL (Legacy) ==========
    # service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/",
    
    # ========== AUTHENTICATION (Required) ==========
    username="your_username",                 # SAP username
    password="your_password",                 # SAP password
    
    # ========== AUTHENTICATION - OAuth (Alternative) ==========
    # client_id="your_client_id",            # OAuth client ID
    # client_secret="your_client_secret",    # OAuth client secret
    
    # ========== SAP-SPECIFIC PARAMETERS (Optional) ==========
    sap_client="100",                         # SAP client number (e.g., '100', '800')
    system_id="ES5",                          # SAP system ID
    
    # ========== OUTPUT SETTINGS ==========
    output_directory="./output",              # Where to save results
    
    # ========== ENTITY SELECTION (Optional) ==========
    selected_modules=["Products", "Orders"],  # Specific entities to process
    
    # ========== PROCESSING LIMITS (Optional) ==========
    total_records_limit=10000,                # Global record limit (None = unlimited)
)
```

---

## 🌐 Connection Methods

### Method 1: Using SAP Module (Recommended) ⭐

**Best for**: Standard SAP modules with automatic service mapping

```python
config = ClientConfig(
    sap_server="sapes5.sapdevcenter.com",
    sap_port=443,
    sap_module="ES5",  # Automatically maps to EPM_REF_APPS_SHOP_SRV
    username="user",
    password="pass"
)
```

**Advantages:**
- ✅ Simple and clean
- ✅ Automatic service name mapping
- ✅ Supports 50+ SAP modules
- ✅ Easy to remember module names

**Supported Modules:** See [SAP Module Mapping](#sap-module-mapping) section

---

### Method 2: Using Service Name Directly

**Best for**: Custom OData services or when you know the exact service name

```python
config = ClientConfig(
    sap_server="mycompany-sap.com",
    sap_port=8000,
    service_name="ZMY_CUSTOM_SERVICE_SRV",  # Your custom service
    username="user",
    password="pass"
)
```

**Advantages:**
- ✅ Works with any OData service
- ✅ Custom services supported
- ✅ Full control over service name

---

### Method 3: Using Full URL (Legacy)

**Best for**: Backward compatibility or complex URL structures

```python
config = ClientConfig(
    service_url="https://server.com/sap/opu/odata/sap/MY_SERVICE_SRV/",
    username="user",
    password="pass"
)
```

**Advantages:**
- ✅ Backward compatible
- ✅ Works with any URL structure
- ✅ No URL construction needed

---

## 🗺️ SAP Module Mapping

The connector supports automatic mapping from module names to OData service names:

### Finance & Controlling (FI/CO)
```python
sap_module="FI"          # → Financial Accounting services
sap_module="CO"          # → Controlling services
sap_module="TR"          # → Treasury services
sap_module="AA"          # → Asset Accounting services
```

### Materials Management (MM)
```python
sap_module="MM"          # → Materials Management services
sap_module="IM"          # → Inventory Management services
sap_module="WM"          # → Warehouse Management services
```

### Sales & Distribution (SD)
```python
sap_module="SD"          # → Sales & Distribution services
sap_module="LE"          # → Logistics Execution services
```

### Production Planning (PP)
```python
sap_module="PP"          # → Production Planning services
sap_module="QM"          # → Quality Management services
sap_module="PM"          # → Plant Maintenance services
```

### Human Resources (HR)
```python
sap_module="HR"          # → Human Resources services
sap_module="PA"          # → Personnel Administration services
sap_module="PY"          # → Payroll services
```

### Cloud Solutions
```python
sap_module="ARIBA"       # → SAP Ariba services
sap_module="CONCUR"      # → SAP Concur services
sap_module="SUCCESSFACTORS"  # → SuccessFactors services
sap_module="FIELDGLASS"  # → SAP Fieldglass services
```

### Demo/Test Systems
```python
sap_module="ES5"         # → EPM_REF_APPS_SHOP_SRV (Demo system)
sap_module="NORTHWIND"   # → Northwind OData service
```

### Check Available Modules

```python
from covasant_odata.config.sap_module_mapping import SAPModuleMapping

# Get all available modules
modules = SAPModuleMapping.get_all_modules()
print(f"Available modules: {modules}")

# Get service name for a module
service = SAPModuleMapping.get_service_name("ES5")
print(f"ES5 maps to: {service}")

# Get module information
info = SAPModuleMapping.get_module_info("FI")
print(f"FI module info: {info}")
```

---

## 🔍 Filtering Guide

### Basic Filter Syntax

OData filters use a specific syntax. Here's the complete guide:

### 1. Comparison Operators

#### Equal (`eq`)
```python
filter_condition="Status eq 'Active'"
filter_condition="Price eq 100"
filter_condition="IsDeleted eq false"
```

#### Not Equal (`ne`)
```python
filter_condition="Status ne 'Deleted'"
filter_condition="Category ne 'Obsolete'"
```

#### Greater Than (`gt`)
```python
filter_condition="Price gt 100"
filter_condition="Quantity gt 0"
```

#### Greater or Equal (`ge`)
```python
filter_condition="Price ge 100"
filter_condition="Stock ge 10"
```

#### Less Than (`lt`)
```python
filter_condition="Price lt 1000"
filter_condition="Stock lt 5"
```

#### Less or Equal (`le`)
```python
filter_condition="Discount le 20"
filter_condition="Quantity le 100"
```

---

### 2. Logical Operators

#### AND
```python
filter_condition="Price gt 100 and Stock lt 10"
filter_condition="Category eq 'Electronics' and Price le 500"
filter_condition="Status eq 'Active' and Quantity gt 0 and Price lt 1000"
```

#### OR
```python
filter_condition="Category eq 'Electronics' or Category eq 'Computers'"
filter_condition="Status eq 'Pending' or Status eq 'Processing'"
```

#### NOT
```python
filter_condition="not (Status eq 'Deleted')"
filter_condition="not (Price gt 1000)"
```

#### Complex Combinations
```python
filter_condition="(Category eq 'A' or Category eq 'B') and Price gt 100"
filter_condition="Status eq 'Active' and (Stock lt 5 or Reorder eq true)"
```

---

### 3. String Functions

#### contains() - Check if string contains substring
```python
filter_condition="contains(Name, 'SAP')"
filter_condition="contains(Description, 'premium')"
filter_condition="contains(Email, '@company.com')"
```

#### startswith() - Check if string starts with
```python
filter_condition="startswith(ProductCode, 'PRD')"
filter_condition="startswith(CustomerID, 'C')"
filter_condition="startswith(Name, 'SAP')"
```

#### endswith() - Check if string ends with
```python
filter_condition="endswith(Email, '@gmail.com')"
filter_condition="endswith(FileName, '.pdf')"
```

#### tolower() / toupper() - Case conversion
```python
filter_condition="tolower(Name) eq 'product a'"
filter_condition="toupper(Status) eq 'ACTIVE'"
```

#### length() - String length
```python
filter_condition="length(ProductCode) eq 10"
filter_condition="length(Name) gt 5"
```

#### substring() - Extract substring
```python
filter_condition="substring(ProductCode, 0, 3) eq 'PRD'"
```

---

### 4. Date and Time Functions

#### Date Comparison
```python
# Using datetime literal
filter_condition="OrderDate ge datetime'2024-01-01T00:00:00'"
filter_condition="CreatedDate lt datetime'2024-12-31T23:59:59'"
```

#### Date Functions
```python
# Year
filter_condition="year(OrderDate) eq 2024"

# Month
filter_condition="month(OrderDate) eq 10"

# Day
filter_condition="day(OrderDate) eq 15"

# Hour, Minute, Second
filter_condition="hour(CreatedTime) ge 9"
filter_condition="minute(CreatedTime) lt 30"
```

#### Dynamic Date Filtering (Python)
```python
from datetime import datetime, timedelta

# Last 30 days
thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S')
filter_condition = f"OrderDate ge datetime'{thirty_days_ago}'"

# Last 6 months
six_months_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%dT%H:%M:%S')
filter_condition = f"ModifiedDate ge datetime'{six_months_ago}'"

# This year
year_start = datetime.now().replace(month=1, day=1).strftime('%Y-%m-%dT00:00:00')
filter_condition = f"OrderDate ge datetime'{year_start}'"

# This month
month_start = datetime.now().replace(day=1).strftime('%Y-%m-%dT00:00:00')
filter_condition = f"OrderDate ge datetime'{month_start}'"
```

---

### 5. Arithmetic Functions

```python
# Add
filter_condition="Price add Tax gt 100"

# Subtract
filter_condition="Stock sub Reserved gt 10"

# Multiply
filter_condition="Quantity mul Price gt 1000"

# Divide
filter_condition="TotalAmount div Quantity lt 50"

# Modulo
filter_condition="OrderNumber mod 2 eq 0"  # Even order numbers
```

---

### 6. Null Checks

```python
# Check if field is null
filter_condition="Email eq null"
filter_condition="DeletedDate eq null"

# Check if field is not null
filter_condition="Email ne null"
filter_condition="ApprovedDate ne null"
```

---

### 7. Collection Functions

#### any() - Check if any item in collection matches
```python
filter_condition="OrderDetails/any(d: d/Quantity gt 10)"
filter_condition="Tags/any(t: t eq 'Premium')"
```

#### all() - Check if all items in collection match
```python
filter_condition="OrderDetails/all(d: d/Status eq 'Shipped')"
```

---

## 📝 Query Options

### Complete get_data() Parameters

```python
result = await connector.get_data(
    # ========== REQUIRED ==========
    entity_name="Products",              # Entity to query
    
    # ========== FILTERING ==========
    filter_condition="Price gt 100",     # OData filter expression
    
    # ========== FIELD SELECTION ==========
    select_fields="Id,Name,Price",       # Comma-separated fields
    
    # ========== RELATIONSHIP EXPANSION (JOINs) ==========
    expand_relations="Supplier,Category", # Comma-separated relations
    
    # ========== SORTING ==========
    order_by="Price desc",               # Field and direction (asc/desc)
    
    # ========== SEARCH ==========
    search_query="electronics",          # Full-text search
    
    # ========== LIMITING ==========
    record_limit=100,                    # Maximum records to fetch
    
    # ========== COUNT ==========
    include_count=True,                  # Include total count
    
    # ========== CUSTOM PARAMETERS ==========
    custom_query_params={                # Custom OData parameters
        "$skip": "10",
        "$format": "json"
    }
)
```

---

## 🎯 Advanced Examples

### Example 1: Complex Business Query
```python
# Get high-value orders from last quarter with customer details
from datetime import datetime, timedelta

quarter_start = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%dT00:00:00')

result = await connector.get_data(
    entity_name="Orders",
    filter_condition=f"OrderDate ge datetime'{quarter_start}' and TotalAmount gt 10000 and Status eq 'Completed'",
    select_fields="Id,OrderDate,TotalAmount,CustomerName,Status",
    expand_relations="Customer,OrderDetails/Product",
    order_by="TotalAmount desc",
    record_limit=100
)
```

### Example 2: Inventory Management Query
```python
# Find low-stock products that need reordering
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Stock lt ReorderLevel and Active eq true and not (Category eq 'Discontinued')",
    select_fields="Id,Name,Stock,ReorderLevel,Category,SupplierName",
    expand_relations="Supplier",
    order_by="Stock asc"
)
```

### Example 3: Customer Analysis Query
```python
# Get premium customers from specific region
result = await connector.get_data(
    entity_name="Customers",
    filter_condition="Country eq 'USA' and (CustomerType eq 'Premium' or TotalPurchases gt 50000) and Active eq true",
    select_fields="Id,CompanyName,Country,TotalPurchases,CustomerType,Email",
    expand_relations="Orders,ContactPersons",
    order_by="TotalPurchases desc",
    record_limit=50
)
```

### Example 4: Date Range with Multiple Conditions
```python
# Get orders from specific date range with specific criteria
from datetime import datetime

start_date = "2024-01-01T00:00:00"
end_date = "2024-12-31T23:59:59"

result = await connector.get_data(
    entity_name="Orders",
    filter_condition=f"OrderDate ge datetime'{start_date}' and OrderDate le datetime'{end_date}' and (Status eq 'Shipped' or Status eq 'Delivered') and TotalAmount gt 100",
    select_fields="Id,OrderDate,Status,TotalAmount,CustomerName",
    expand_relations="Customer,ShippingAddress",
    order_by="OrderDate desc"
)
```

### Example 5: String Search with Multiple Conditions
```python
# Find products with specific keywords in name or description
result = await connector.get_data(
    entity_name="Products",
    filter_condition="(contains(Name, 'laptop') or contains(Description, 'laptop')) and Price ge 500 and Price le 2000 and Stock gt 0",
    select_fields="Id,Name,Description,Price,Stock",
    expand_relations="Category,Supplier",
    order_by="Price asc"
)
```

### Example 6: Nested Expansion
```python
# Get orders with full hierarchy: Order → OrderDetails → Product → Supplier
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="Status eq 'Processing'",
    expand_relations="Customer,OrderDetails/Product/Supplier,ShippingAddress",
    order_by="OrderDate desc"
)
```

### Example 7: Using Multiple Modules
```python
# Query different SAP modules
config_fi = ClientConfig(
    sap_server="server.com",
    sap_port=443,
    sap_module="FI",  # Financial Accounting
    username="user",
    password="pass"
)

config_mm = ClientConfig(
    sap_server="server.com",
    sap_port=443,
    sap_module="MM",  # Materials Management
    username="user",
    password="pass"
)

# Query FI module
connector_fi = SAPODataConnector(config_fi)
await connector_fi.initialize()
gl_accounts = await connector_fi.get_data(entity_name="GLAccounts")

# Query MM module
connector_mm = SAPODataConnector(config_mm)
await connector_mm.initialize()
materials = await connector_mm.get_data(entity_name="Materials")
```

---

## 📊 Filter Operators Quick Reference

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `Status eq 'Active'` |
| `ne` | Not equal | `Status ne 'Deleted'` |
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
| `tolower()` | Convert to lowercase | `tolower(Name) eq 'product'` |
| `toupper()` | Convert to uppercase | `toupper(Status) eq 'ACTIVE'` |
| `length()` | String length | `length(Code) eq 10` |
| `year()` | Extract year | `year(OrderDate) eq 2024` |
| `month()` | Extract month | `month(OrderDate) eq 10` |
| `day()` | Extract day | `day(OrderDate) eq 15` |
| `add` | Addition | `Price add Tax gt 100` |
| `sub` | Subtraction | `Stock sub Reserved gt 10` |
| `mul` | Multiplication | `Quantity mul Price gt 1000` |
| `div` | Division | `Total div Quantity lt 50` |
| `mod` | Modulo | `OrderNumber mod 2 eq 0` |

---

## 💡 Best Practices

### 1. Use Specific Filters
```python
# ✅ Good - filter on server
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)

# ❌ Bad - fetch all then filter in Python
all_products = await connector.get_data(entity_name="Products")
filtered = [p for p in all_products if p['Price'] > 100]
```

### 2. Select Only Needed Fields
```python
# ✅ Good - select specific fields
result = await connector.get_data(
    entity_name="Products",
    select_fields="Id,Name,Price"
)

# ❌ Bad - fetch all fields
result = await connector.get_data(entity_name="Products")
```

### 3. Use Expansion for Related Data
```python
# ✅ Good - one query with expansion
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier,Category"
)

# ❌ Bad - multiple queries
products = await connector.get_data(entity_name="Products")
for product in products:
    supplier = await connector.get_data(entity_name="Suppliers", ...)
```

### 4. Test Filters with Limits
```python
# ✅ Good - test with small limit first
test = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100",
    record_limit=5
)
# Verify results, then fetch all
full = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

---

## 🆘 Troubleshooting

### Invalid Filter Syntax
```python
# ❌ Wrong
filter_condition="Price > 100"  # Use 'gt' not '>'

# ✅ Correct
filter_condition="Price gt 100"
```

### Date Format Issues
```python
# ❌ Wrong
filter_condition="OrderDate ge '2024-01-01'"

# ✅ Correct
filter_condition="OrderDate ge datetime'2024-01-01T00:00:00'"
```

### String Comparison
```python
# ❌ Wrong
filter_condition="Status eq Active"  # Missing quotes

# ✅ Correct
filter_condition="Status eq 'Active'"
```

---

## 📚 Additional Resources

- **OData Protocol**: https://www.odata.org/documentation/
- **OData Query Options**: https://www.odata.org/getting-started/basic-tutorial/#queryData
- **SAP OData Documentation**: https://help.sap.com/docs/odata

---

**Package**: `covasant_sap_odata_connector` | **Version**: 1.0.0
