# SAP Connector - New Modular Architecture

## 🎯 Overview

The SAP Connector has been restructured to support multiple SAP service types (OData, RFC, REST, SOAP) with a simplified configuration approach where only credentials are configured upfront, and execution parameters are provided at runtime.

## ✅ Key Changes Made

### 1. **Service Type Selection**
```python
from odc.config.models import ServiceType

# Choose your SAP service type
config = ClientConfig(
    service_type=ServiceType.ODATA,  # or RFC, REST, SOAP (future)
    service_url="https://your-sap-service.com",
    username="your_username",
    password="your_password"
)
```

### 2. **Simplified Configuration (Credentials Only)**

**Before (Complex Config):**
```python
config = ClientConfig(
    odata_service_url="https://...",
    username="user",
    password="pass",
    selected_modules=["Products"],     # ❌ Removed
    total_records_limit=100,          # ❌ Removed  
    batch_size=50,                    # ❌ Removed
    max_workers=5,                    # ❌ Removed
    requests_per_second=5.0,          # ❌ Removed
    output_directory="./output",
    raw_data_directory="./raw",       # ❌ Removed
    processed_data_directory="./proc" # ❌ Removed
)
```

**After (Simple Config):**
```python
config = ClientConfig(
    service_type=ServiceType.ODATA,   # ✅ New: Service type
    service_url="https://...",        # ✅ Renamed from odata_service_url
    username="user",                  # ✅ Credentials only
    password="pass",                  # ✅ Credentials only
    output_directory="./output"       # ✅ Simple storage
)
```

### 3. **Runtime Execution Parameters**

**Before (Fixed in Config):**
```python
# Parameters were fixed at configuration time
await connector.get_data()
```

**After (Flexible at Runtime):**
```python
# Parameters provided when calling get_data()
await connector.get_data(
    entity_name="Products",
    filter_condition="UnitPrice gt 20",
    record_limit=100,
    batch_size=50,              # ✅ Runtime parameter
    max_workers=5,              # ✅ Runtime parameter  
    requests_per_second=10.0,   # ✅ Runtime parameter
    enable_parallel_processing=True
)
```

## 🏭 Factory Pattern for Service Types

```python
from odc.config.models import ConnectorFactory

# Automatically creates the right connector based on service_type
connector = ConnectorFactory.create_connector(config)

# Future service types:
# - ServiceType.ODATA → SAPODataConnector (implemented)
# - ServiceType.RFC → SAPRFCConnector (future)
# - ServiceType.REST → SAPRESTConnector (future)  
# - ServiceType.SOAP → SAPSOAPConnector (future)
```

## 📊 New Configuration Classes

### 1. **ClientConfig** (Simplified)
```python
@dataclass
class ClientConfig:
    service_type: ServiceType           # NEW: Service selection
    service_url: str                   # Renamed from odata_service_url
    username: Optional[str] = None     # Credentials only
    password: Optional[str] = None
    client_id: Optional[str] = None    # OAuth support
    client_secret: Optional[str] = None
    client: Optional[str] = None       # NEW: SAP client (for RFC)
    system_id: Optional[str] = None    # NEW: SAP system ID
    output_directory: str = "./output" # Simple storage
```

### 2. **ExecutionConfig** (Runtime Parameters)
```python
@dataclass  
class ExecutionConfig:
    selected_entities: Optional[List[str]] = None
    total_records_limit: Optional[int] = None
    batch_size: int = 1000
    max_workers: int = 5
    requests_per_second: float = 5.0
    enable_parallel_processing: bool = True
    enable_caching: bool = False
```

## 🚀 Usage Examples

### Basic Usage
```python
# 1. Simple configuration
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
    output_directory="./data"
)

# 2. Create connector
connector = ConnectorFactory.create_connector(config)

# 3. Initialize
entities = await connector.initialize()

# 4. Get data with runtime parameters
result = await connector.get_data(
    entity_name="Products",
    record_limit=50,
    batch_size=25,
    max_workers=3
)
```

### Different Execution Scenarios
```python
# Conservative settings for small datasets
await connector.get_data(
    entity_name="Categories", 
    batch_size=10,
    max_workers=2,
    requests_per_second=2.0
)

# Aggressive settings for large datasets  
await connector.get_data(
    entity_name="Orders",
    batch_size=1000,
    max_workers=10,
    requests_per_second=20.0
)

# Filtered queries
await connector.get_data(
    entity_name="Products",
    filter_condition="UnitPrice gt 50",
    batch_size=100,
    max_workers=5
)
```

## 🔮 Future Service Types

### RFC Connector (Future)
```python
config = ClientConfig(
    service_type=ServiceType.RFC,
    service_url="sapgw00://server:3300",
    username="user",
    password="pass",
    client="100",
    system_id="DEV"
)

result = await connector.get_data(
    function_name="BAPI_CUSTOMER_GETLIST",
    parameters={"MAX_ROWS": 100}
)
```

### REST Connector (Future)
```python
config = ClientConfig(
    service_type=ServiceType.REST,
    service_url="https://api.sap.com/v1",
    client_id="client_id",
    client_secret="client_secret"
)

result = await connector.get_data(
    endpoint="/customers",
    method="GET"
)
```

## 📁 Updated File Structure

```
odc/
├── config/
│   ├── models.py          # ✅ Updated with ServiceType, simplified ClientConfig
│   └── settings.py        # ✅ Updated env prefix
├── connector.py           # ✅ Updated with service type validation
├── examples/
│   ├── new_api_usage.py   # ✅ New example showing all features
│   └── filter_usage_example.py
└── test_northwind.py      # ✅ Updated to use new config
```

## 🎯 Benefits

### ✅ **Flexibility**
- Different execution parameters per call
- Support for multiple SAP service types
- Runtime optimization based on data size

### ✅ **Simplicity** 
- Configuration only contains credentials
- No need to guess optimal settings upfront
- Clear separation of concerns

### ✅ **Extensibility**
- Easy to add new service types (RFC, REST, SOAP)
- Factory pattern handles connector creation
- Consistent API across service types

### ✅ **Backward Compatibility**
- Existing OData functionality preserved
- Legacy methods still available
- Gradual migration path

## 🧪 Testing the New API

```bash
# Test the new configuration structure
python odc/test_northwind.py

# Test the new API examples
python examples/new_api_usage.py
```

## 🔄 Migration Guide

### From Old API:
```python
# Old way
config = ClientConfig(
    odata_service_url="https://...",
    batch_size=100,
    max_workers=5
)
connector = SAPODataConnector(config)
result = await connector.get_data()
```

### To New API:
```python  
# New way
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://..."
)
connector = ConnectorFactory.create_connector(config)
result = await connector.get_data(
    batch_size=100,
    max_workers=5
)
```

---

**Summary**: The SAP Connector is now a modular, multi-service platform with simplified configuration and flexible runtime parameters, ready for future expansion to RFC, REST, and SOAP services! 🚀
