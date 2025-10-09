# CLI Quick Start Guide

## ✅ CLI is Installed and Working!

Your SAP OData Connector now has a **command-line interface (CLI)** for easy data extraction.

---

## How to Use the CLI

### Method 1: Using Python Module (Recommended)

```bash
python -m covasant_odata.cli [COMMAND] [OPTIONS]
```

### Method 2: Direct Script (if in PATH)

```bash
sap-odata-connector [COMMAND] [OPTIONS]
```

---

## Quick Examples

### 1. Show Help

```bash
python -m covasant_odata.cli --help
```

### 2. List Available Entities

```bash
python -m covasant_odata.cli list-entities --url https://services.odata.org/V4/Northwind/Northwind.svc/
```

### 3. Fetch All Products

```bash
python -m covasant_odata.cli fetch --url https://services.odata.org/V4/Northwind/Northwind.svc/ --entity Products
```

### 4. Fetch with Filter

```bash
python -m covasant_odata.cli fetch \
  --url https://services.odata.org/V4/Northwind/Northwind.svc/ \
  --entity Products \
  --filter "UnitPrice gt 20" \
  --limit 50
```

### 5. Fetch from SAP EPM Service

```bash
python -m covasant_odata.cli fetch \
  --server sapes5.sapdevcenter.com \
  --module ES5 \
  --user P2010682507 \
  --password Bhuvan@2001 \
  --entity Products
```

---

## Available Commands

| Command | Description |
|---------|-------------|
| `fetch` | Fetch data from OData service |
| `list-entities` | List all available entities |
| `metadata` | Export service metadata to JSON |

---

## Common Options for `fetch`

| Option | Description | Example |
|--------|-------------|---------|
| `--url` | OData service URL | `--url https://service.com/` |
| `--entity` | Specific entity to fetch | `--entity Products` |
| `--filter` | OData filter condition | `--filter "Price gt 100"` |
| `--select` | Select specific fields | `--select "Id,Name,Price"` |
| `--expand` | Expand relations | `--expand "Supplier,Category"` |
| `--limit` | Maximum records | `--limit 100` |
| `--output` | Output directory | `--output ./my_data` |

---

## Full Documentation

For complete CLI documentation, see: **[CLI_USAGE_GUIDE.md](CLI_USAGE_GUIDE.md)**

---

## Test It Now!

Try this command to see it in action:

```bash
python -m covasant_odata.cli list-entities --url https://services.odata.org/V4/Northwind/Northwind.svc/
```

This will list all 26 entities available in the Northwind V4 service!

---

**Happy Data Extracting! 🚀**
