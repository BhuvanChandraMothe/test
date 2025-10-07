# SAP OData Connector - Usage Cheat Sheet

## 📦 Installation

```bash
pip install sap-odata-connector-testcov
```

## 🔑 Key Point

**Package name**: `sap-odata-connector-testcov` (for pip install)  
**Import name**: `odc` (for Python code)

```python
# ✅ Correct
from odc.connector import SAPODataConnector

# ❌ Wrong
from sap-odata-connector-tescov import *
```

## 🚀 Quick Start

```python
import asyncio
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def main():
    config = ClientConfig(
        service_url="https://server.com/sap/opu/odata/sap/SERVICE/",
        username="user",
        password="pass",
        output_directory="./output"
    )
    
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    result = await connector.get_data(entity_name="Products")
    print(f"Got {result['execution_stats']['records_processed']} records")
    
    await connector.cleanup()

asyncio.run(main())
```

## 📝 Common Queries

### Simple Query
```python
result = await connector.get_data(entity_name="Products")
```

### With Filter
```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

### With JOIN (Expand)
```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)
```

### With Multiple Options
```python
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="Status eq 'Completed'",
    select_fields="Id,Date,Total",
    order_by="Date desc",
    record_limit=100
)
```

## 📊 Output

Results are auto-saved to:
- `./output/query_results/YYYYMMDD_HHMMSS_entityname.json`
- Unique filenames based on query parameters

## ✅ Verify Installation

```bash
python -c "from odc.connector import SAPODataConnector; print('Works!')"
```

## 🆘 Troubleshooting

**Error: "No module named 'odc'"**
- Solution: `pip install sap-odata-connector-testcov`

**Error: "No module named 'odc.utils'"**
- Solution: Install latest version from PyPI

## 📚 More Info

- PyPI: https://pypi.org/project/sap-odata-connector-testcov/
- Full docs: See README.md or USER_GUIDE.md
