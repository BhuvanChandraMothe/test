# SAP OData Connector - User Guide

## Installation

Install from PyPI:

```bash
pip install sap-odata-connector-tescov
```

## Quick Start

```python
import asyncio
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def main():
    # Configure the connector
    config = ClientConfig(
        service_url="https://your-sap-server.com/sap/opu/odata/sap/SERVICE_NAME/",
        username="your_username",
        password="your_password",
        output_directory="./output"
    )
    
    # Create connector
    connector = SAPODataConnector(config)
    
    try:
        # Initialize
        await connector.initialize()
        
        # Query data
        result = await connector.get_data(entity_name="Products")
        print(f"Retrieved {result['execution_stats']['records_processed']} products")
        
    finally:
        await connector.cleanup()

# Run
asyncio.run(main())
```

## Important Notes

### Package vs Import Name

- **Install with**: `pip install sap-odata-connector-tescov`
- **Import with**: `from odc.connector import ...`

The package name on PyPI is `sap-odata-connector-tescov`, but you import using `odc`.

### Common Imports

```python
# Main connector
from odc.connector import SAPODataConnector

# Configuration
from odc.config.models import ClientConfig

# Storage (if needed)
from odc.storage.local_storage import LocalStorage
from odc.storage.bigquery_storage import BigQueryStorage
```

## Basic Usage Examples

### 1. Simple Query

```python
result = await connector.get_data(entity_name="Products")
```

### 2. Query with Filter

```python
result = await connector.get_data(
    entity_name="Products",
    filter_condition="Price gt 100"
)
```

### 3. Query with Expansion (JOIN)

```python
result = await connector.get_data(
    entity_name="Products",
    expand_relations="Supplier"
)
```

### 4. Query with Multiple Options

```python
result = await connector.get_data(
    entity_name="Orders",
    filter_condition="Status eq 'Completed'",
    select_fields="Id,OrderDate,Total",
    order_by="OrderDate desc",
    record_limit=100
)
```

## Features

✅ Automatic pagination  
✅ Relationship expansion ($expand)  
✅ Advanced filtering ($filter)  
✅ Field selection ($select)  
✅ Ordering ($orderby)  
✅ Automatic file saving with unique names  
✅ Clean professional logging  
✅ BigQuery integration (optional)  

## Output Files

Query results are automatically saved to JSON files with unique names:

- `20251006_144807_products.json`
- `20251006_144807_products_expand_Supplier.json`
- `20251006_144807_products_filter_Price_greater_100.json`

## Requirements

- Python >= 3.8
- All dependencies are automatically installed with the package

## Support

For issues and questions:
- GitHub: [Your repo URL]
- Email: [Your email]

## License

MIT License
