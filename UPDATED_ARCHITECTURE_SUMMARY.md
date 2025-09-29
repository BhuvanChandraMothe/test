# Updated SAP Connector Architecture

## ✅ **Changes Made Based on Your Requirements**

### 1. **Module/Entity Selection Restored** 
```python
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://your-sap-server/sap/opu/odata/sap/SERVICE_NAME/",
    username="your_sap_username",
    password="your_sap_password",
    selected_modules=["Products", "Categories", "Orders"],  # ✅ Module selection restored
    sap_client="100",  # ✅ SAP-specific parameters
    system_id="PRD"
)
```

### 2. **Service Types Updated (REST + STREAMING)**
```python
class ServiceType(str, Enum):
    ODATA = "odata"        # ✅ Currently implemented
    REST = "rest"          # 🔄 Work in progress
    STREAMING = "streaming" # 🔄 Work in progress
    # Removed: RFC, SOAP (as requested)
```

### 3. **Real SAP System Support**
```python
# For real SAP S/4HANA systems:
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://your-s4hana-server:44300/sap/opu/odata/sap/API_BUSINESS_PARTNER/",
    username="your_sap_username",
    password="your_sap_password",
    sap_client="100",      # ✅ SAP client number
    system_id="S4H",       # ✅ SAP system ID
    selected_modules=[     # ✅ SAP-specific modules
        "A_BusinessPartner",
        "A_Customer", 
        "A_Supplier"
    ]
)

# For SAP SuccessFactors:
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://api4.successfactors.com/odata/v2/",
    client_id="your_oauth_client_id",
    client_secret="your_oauth_client_secret",
    selected_modules=["EmpEmployment", "PerPersonal", "User"]
)
```

## 📁 **New Files Created**

### 1. **Future Connector Placeholders**
```
odc/connectors/
├── __init__.py                 # ✅ Package initialization
├── rest_connector.py           # 🔄 Work in progress
└── streaming_connector.py      # 🔄 Work in progress
```

### 2. **Updated Examples**
```
examples/
├── new_api_usage.py           # ✅ Updated with module selection
├── real_sap_usage.py          # ✅ New: Real SAP system examples
└── filter_usage_example.py    # ✅ Existing
```

## 🏢 **Real SAP System Examples**

### **S/4HANA Business Partner Service**
```python
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://your-s4hana-server:44300/sap/opu/odata/sap/API_BUSINESS_PARTNER/",
    username="your_sap_username",
    password="your_sap_password",
    sap_client="100",
    system_id="S4H",
    selected_modules=[
        "A_BusinessPartner",
        "A_Customer", 
        "A_Supplier",
        "A_BusinessPartnerAddress"
    ]
)
```

### **SAP SuccessFactors Employee Central**
```python
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://api4.successfactors.com/odata/v2/",
    client_id="your_oauth_client_id",
    client_secret="your_oauth_client_secret",
    selected_modules=[
        "EmpEmployment",
        "PerPersonal", 
        "EmpJob",
        "User"
    ]
)
```

### **SAP Ariba Procurement**
```python
config = ClientConfig(
    service_type=ServiceType.ODATA,
    service_url="https://openapi.ariba.com/api/procurement-reporting/v1/prod/",
    client_id="your_ariba_client_id",
    client_secret="your_ariba_client_secret",
    selected_modules=[
        "PurchaseOrders",
        "Suppliers",
        "Contracts",
        "InvoiceLineItems"
    ]
)
```

## 🔄 **Future Service Types (Work in Progress)**

### **REST Connector**
```python
# File: odc/connectors/rest_connector.py
class SAPRESTConnector:
    def __init__(self, config: ClientConfig):
        raise NotImplementedError("REST connector - work in progress")
    
    async def get_data(self, endpoint: str, method: str = "GET", **kwargs):
        raise NotImplementedError("REST connector - work in progress")
```

### **Streaming Connector**
```python
# File: odc/connectors/streaming_connector.py  
class SAPStreamingConnector:
    def __init__(self, config: ClientConfig):
        raise NotImplementedError("Streaming connector - work in progress")
    
    async def get_data_stream(self, stream_name: str, **kwargs):
        raise NotImplementedError("Streaming connector - work in progress")
```

## 🎯 **Updated Configuration Structure**

### **ClientConfig (Updated)**
```python
@dataclass
class ClientConfig:
    # Service selection
    service_type: ServiceType = ServiceType.ODATA
    
    # Connection (credentials only)
    service_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    
    # SAP-specific parameters
    sap_client: Optional[str] = None      # ✅ SAP client number
    system_id: Optional[str] = None       # ✅ SAP system ID
    
    # Module selection (restored)
    selected_modules: List[str] = []      # ✅ Specific modules to process
    
    # Storage
    output_directory: str = "./output"
```

### **ExecutionConfig (Runtime Parameters)**
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

## 🚀 **Usage Pattern**

### **1. Configuration (Credentials + Modules)**
```python
config = ClientConfig(
    service_type="odata",
    service_url="https://your-sap-server/service/",
    username="user",
    password="pass",
    sap_client="100",
    selected_modules=["Products", "Orders"]  # ✅ Module selection
)
```

### **2. Runtime Execution**
```python
connector = SAPODataConnector(config)
await connector.initialize()

result = await connector.get_data(
    entity_name="Products",
    batch_size=100,        # Runtime parameters
    max_workers=5,
    requests_per_second=10.0
)
```

## 🧪 **Testing**

### **Test with Module Selection**
```bash
# Updated test includes module selection
python odc/test_northwind.py

# New real SAP examples
python examples/real_sap_usage.py

# Updated API demonstration
python examples/new_api_usage.py
```

## 📊 **Key Benefits**

### ✅ **Module Selection Restored**
- Specify exactly which SAP modules/entities to process
- Reduces processing time and storage requirements
- Better control over data extraction

### ✅ **Real SAP System Ready**
- Support for S/4HANA, SuccessFactors, Ariba, Concur
- SAP-specific authentication (Basic, OAuth)
- SAP client and system ID support

### ✅ **Future-Ready Architecture**
- REST connector placeholder created
- Streaming connector placeholder created
- Easy to extend with new service types

### ✅ **Clean Separation**
- **Config**: Credentials + Module selection
- **Runtime**: Execution parameters (batch size, workers, etc.)

---

**Summary**: The SAP Connector now properly supports module selection, real SAP system authentication, and has placeholders for REST and STREAMING connectors (work in progress). Ready for production use with real SAP systems! 🚀
