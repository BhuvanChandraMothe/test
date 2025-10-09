# SAP OData Connector - CLI Usage Guide

## Installation

First, install the package (which includes the CLI):

```bash
pip install -e .
```

After installation, the `sap-odata-connector` command will be available globally.

---

## Quick Start

### 1. List Available Entities

See what entities are available in a service:

```bash
sap-odata-connector list-entities --url https://services.odata.org/V4/Northwind/Northwind.svc/
```

### 2. Fetch All Data

Fetch all entities from a service:

```bash
sap-odata-connector fetch --url https://services.odata.org/V4/Northwind/Northwind.svc/
```

### 3. Fetch Specific Entity

Fetch a single entity:

```bash
sap-odata-connector fetch --url https://services.odata.org/V4/Northwind/Northwind.svc/ --entity Products
```

---

## Commands

### `fetch` - Extract Data

Fetch data from an OData service.

**Basic Usage:**
```bash
sap-odata-connector fetch [OPTIONS]
```

**Options:**

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--url` | `-u` | Full OData service URL | `--url https://service.com/odata/` |
| `--server` | `-s` | SAP server hostname | `--server sapes5.sapdevcenter.com` |
| `--port` | `-p` | SAP server port (default: 443) | `--port 8000` |
| `--module` | `-m` | SAP module name | `--module ES5` |
| `--service` | | OData service name | `--service EPM_REF_APPS_SHOP_SRV` |
| `--user` | | Username for authentication | `--user P2010682507` |
| `--password` | | Password for authentication | `--password yourpass` |
| `--entity` | `-e` | Specific entity to fetch | `--entity Products` |
| `--entities` | | Comma-separated entities | `--entities Products,Orders,Customers` |
| `--filter` | `-f` | OData $filter condition | `--filter "Price gt 100"` |
| `--select` | | OData $select fields | `--select "Id,Name,Price"` |
| `--expand` | | OData $expand relations | `--expand "Supplier,Category"` |
| `--orderby` | | OData $orderby clause | `--orderby "Price desc"` |
| `--limit` | `-l` | Maximum records to fetch | `--limit 100` |
| `--batch-size` | | Records per batch (default: 1000) | `--batch-size 500` |
| `--output` | `-o` | Output directory (default: ./output) | `--output ./my_data` |
| `--workers` | | Parallel workers (default: 5) | `--workers 10` |
| `--timeout` | | Request timeout in seconds | `--timeout 120` |

---

### `list-entities` - List Available Entities

List all entities available in the service.

**Usage:**
```bash
sap-odata-connector list-entities [OPTIONS]
```

**Example:**
```bash
sap-odata-connector list-entities --url https://services.odata.org/V4/Northwind/Northwind.svc/
```

**Output:**
```
======================================================================
Available Entities
======================================================================
Service: https://services.odata.org/V4/Northwind/Northwind.svc/

Total Entities: 26
Total Records: 11,400

Entity Name                    Records         Properties     
----------------------------------------------------------------------
Products                              77             20
Orders                               830             14
Customers                             91             11
...
```

---

### `metadata` - Export Service Metadata

Export service metadata to a JSON file.

**Usage:**
```bash
sap-odata-connector metadata [OPTIONS]
```

**Example:**
```bash
sap-odata-connector metadata --url https://services.odata.org/V4/Northwind/Northwind.svc/ -o northwind_metadata.json
```

**Output:**
```
Exporting metadata from: https://services.odata.org/V4/Northwind/Northwind.svc/
✓ Metadata exported successfully!
  - File: northwind_metadata.json
  - Size: 45.23 KB
  - Entities: 26
  - Total Records: 11,400
```

---

## Connection Methods

### Method 1: Using Full URL (Simplest)

```bash
sap-odata-connector fetch --url https://services.odata.org/V4/Northwind/Northwind.svc/
```

### Method 2: Using SAP Module (Recommended for SAP)

```bash
sap-odata-connector fetch \
  --server sapes5.sapdevcenter.com \
  --module ES5 \
  --user P2010682507 \
  --password yourpass
```

### Method 3: Using Service Name

```bash
sap-odata-connector fetch \
  --server sapes5.sapdevcenter.com \
  --service EPM_REF_APPS_SHOP_SRV \
  --user P2010682507 \
  --password yourpass
```

---

## Examples

### Example 1: Fetch All Products from Northwind V4

```bash
sap-odata-connector fetch \
  --url https://services.odata.org/V4/Northwind/Northwind.svc/ \
  --entity Products \
  --output ./northwind_data
```

### Example 2: Fetch Products with Filter

```bash
sap-odata-connector fetch \
  --url https://services.odata.org/V4/Northwind/Northwind.svc/ \
  --entity Products \
  --filter "UnitPrice gt 20" \
  --limit 50
```

### Example 3: Fetch with Select and Expand

```bash
sap-odata-connector fetch \
  --url https://services.odata.org/V4/Northwind/Northwind.svc/ \
  --entity Products \
  --select "ProductID,ProductName,UnitPrice" \
  --expand "Supplier,Category" \
  --orderby "UnitPrice desc"
```

### Example 4: Fetch from SAP EPM Service

```bash
sap-odata-connector fetch \
  --server sapes5.sapdevcenter.com \
  --module ES5 \
  --user P2010682507 \
  --password Bhuvan@2001 \
  --entity Products \
  --output ./sap_data
```

### Example 5: Fetch Multiple Entities

```bash
sap-odata-connector fetch \
  --url https://services.odata.org/V4/Northwind/Northwind.svc/ \
  --entities Products,Orders,Customers \
  --batch-size 500 \
  --workers 3
```

### Example 6: Fetch with Complex Filter

```bash
sap-odata-connector fetch \
  --url https://services.odata.org/V4/Northwind/Northwind.svc/ \
  --entity Orders \
  --filter "OrderDate ge 2020-01-01 and Freight gt 50" \
  --orderby "OrderDate desc" \
  --limit 100
```

### Example 7: Export Metadata Only

```bash
sap-odata-connector metadata \
  --url https://services.odata.org/V4/Northwind/Northwind.svc/ \
  --output ./northwind_schema.json
```

---

## Output Structure

After running a fetch command, your output directory will contain:

```
./output/
├── query_results/              # Individual query results
│   └── 20251009_103045_products.json
├── processed/                  # Processed data by entity
│   ├── Products/
│   │   └── Products.json
│   ├── Orders/
│   │   └── Orders.json
│   └── ...
├── raw/                        # Raw API responses (for debugging)
│   └── ...
└── entity_relationships.json   # Entity relationship metadata
```

---

## Filter Syntax Quick Reference

### Comparison Operators
```bash
--filter "Price eq 100"          # Equal
--filter "Price ne 100"          # Not equal
--filter "Price gt 100"          # Greater than
--filter "Price ge 100"          # Greater or equal
--filter "Price lt 100"          # Less than
--filter "Price le 100"          # Less or equal
```

### Logical Operators
```bash
--filter "Price gt 100 and Stock lt 10"                    # AND
--filter "Category eq 'A' or Category eq 'B'"              # OR
--filter "not (Status eq 'Deleted')"                       # NOT
--filter "(Price gt 100 or Discount gt 10) and Active eq true"  # Complex
```

### String Functions
```bash
--filter "contains(Name, 'SAP')"              # Contains
--filter "startswith(Code, 'PRD')"            # Starts with
--filter "endswith(Email, '@company.com')"    # Ends with
```

### Date Functions
```bash
--filter "OrderDate ge 2024-01-01"            # Date comparison
--filter "year(OrderDate) eq 2024"            # Year
--filter "month(OrderDate) eq 10"             # Month
```

---

## Tips & Best Practices

### 1. Test with Limits First
```bash
# Test your query with a small limit first
sap-odata-connector fetch --url ... --entity Products --limit 10

# Then fetch all
sap-odata-connector fetch --url ... --entity Products
```

### 2. Use Filters to Reduce Data
```bash
# Only fetch what you need
sap-odata-connector fetch --url ... --entity Orders --filter "OrderDate ge 2024-01-01"
```

### 3. Select Specific Fields
```bash
# Reduce network traffic by selecting only needed fields
sap-odata-connector fetch --url ... --entity Products --select "Id,Name,Price"
```

### 4. Adjust Workers for Performance
```bash
# More workers for faster processing (if server allows)
sap-odata-connector fetch --url ... --workers 10

# Fewer workers for slower/rate-limited servers
sap-odata-connector fetch --url ... --workers 2
```

### 5. Increase Timeout for Slow Services
```bash
sap-odata-connector fetch --url ... --timeout 120
```

---

## Troubleshooting

### Error: "You must provide either --url or --server"

**Solution:** Provide connection details:
```bash
sap-odata-connector fetch --url https://your-service.com/
```

### Error: "Authentication required"

**Solution:** Add credentials:
```bash
sap-odata-connector fetch --url ... --user username --password password
```

### Error: "Connection timeout"

**Solution:** Increase timeout:
```bash
sap-odata-connector fetch --url ... --timeout 120
```

### Error: "Invalid filter syntax"

**Solution:** Check OData filter syntax:
```bash
# Wrong
--filter "Price > 100"

# Correct
--filter "Price gt 100"
```

---

## Getting Help

### Show all commands:
```bash
sap-odata-connector --help
```

### Show help for a specific command:
```bash
sap-odata-connector fetch --help
sap-odata-connector list-entities --help
sap-odata-connector metadata --help
```

### Show version:
```bash
sap-odata-connector --version
```

---

## Advanced Usage

### Piping Output

```bash
# List entities and save to file
sap-odata-connector list-entities --url ... > entities.txt

# Fetch and process with jq
sap-odata-connector metadata --url ... -o - | jq '.entities | keys'
```

### Batch Processing

```bash
# Fetch multiple services in sequence
for service in service1 service2 service3; do
  sap-odata-connector fetch --url "https://$service.com/" --output "./$service"
done
```

### Scheduled Extraction

```bash
# Add to crontab for daily extraction
0 2 * * * sap-odata-connector fetch --url ... --output ./daily_data/$(date +\%Y\%m\%d)
```

---

## Package Information

- **Package**: `covasant_sap_odata_connector`
- **Version**: 1.0.2
- **OData Support**: V2 & V4
- **CLI Command**: `sap-odata-connector`

---

**Happy Data Extracting! 🚀**
