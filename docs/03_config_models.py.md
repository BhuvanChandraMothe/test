# config/models.py - Configuration Models Documentation

## Overview
The `config/models.py` file defines the configuration data models used throughout the SAP OData Connector. It uses Pydantic for validation and attrs for data classes, providing type safety and automatic validation.

## File Structure Analysis

### Imports and Dependencies
```python
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import attrs
from dynaconf import Dynaconf
```

**Library Concepts:**
- **Pydantic**: Data validation library using Python type hints
- **attrs**: Alternative to dataclasses with more features
- **dynaconf**: Configuration management with environment support
- **typing**: Type hints for better code documentation and IDE support

### ClientConfig Class (Pydantic Model)
```python
class ClientConfig(BaseModel):
    """Client configuration holding credentials, modules, and processing settings"""
    
    # OData service settings
    odata_service_url: str = Field(..., description="Full OData service URL")
    
    # Authentication (optional for public services like Northwind)
    username: Optional[str] = Field(None, description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")
```

**Pydantic Field Concepts:**
- `Field(...)`: Required field (ellipsis means required)
- `Field(None)`: Optional field with None default
- `description`: Documentation for API generation
- `Optional[str]`: Type hint indicating value can be None

### Processing Configuration
```python
    # Processing settings
    selected_modules: List[str] = Field(default_factory=list, description="Entity sets to process")
    total_records_limit: Optional[int] = Field(None, description="Maximum records to process")
    batch_size: int = Field(default=1000, description="Records per batch")
    max_workers: int = Field(default=5, description="Maximum concurrent workers")
    
    # Rate limiting
    requests_per_second: float = Field(default=5.0, description="Rate limit for API calls")
```

**Default Value Patterns:**
- `default_factory=list`: Creates new list instance for each object
- `default=1000`: Simple default value
- `Optional[int]`: Can be None or integer
- `float`: Allows decimal values for rate limiting

### Storage Configuration
```python
    # Local storage settings
    output_directory: str = Field(default="./output", description="Local output directory")
    raw_data_directory: str = Field(default="./output/raw", description="Raw data storage directory")
    processed_data_directory: str = Field(default="./output/processed", description="Processed data storage directory")
    
    class Config:
        env_prefix = "ODATA_CONNECTOR_"
```

**Configuration Patterns:**
- **Hierarchical defaults**: Sensible directory structure
- **Environment variable support**: `env_prefix` allows ENV var overrides
- **Path conventions**: Standard directory layout for data organization

### ODataConfig Class (attrs-based)
```python
@attrs.define
class ODataConfig:
    """OData service configuration and request parameters"""
    
    service_url: str = attrs.field()
    username: Optional[str] = attrs.field(default=None)
    password: Optional[str] = attrs.field(default=None)
    client_id: Optional[str] = attrs.field(default=None)
    client_secret: Optional[str] = attrs.field(default=None)
    
    # Request parameters
    timeout: int = attrs.field(default=30)
    verify_ssl: bool = attrs.field(default=True)
    max_retries: int = attrs.field(default=3)
```

**attrs vs Pydantic Comparison:**
- **attrs**: Faster, simpler, less validation
- **Pydantic**: More validation, JSON serialization, API integration
- **Use case**: attrs for internal models, Pydantic for external APIs

### URL Generation Methods
```python
    @property
    def metadata_url(self) -> str:
        """Get the metadata endpoint URL"""
        return f"{self.service_url}/$metadata"
    
    def entity_set_url(self, entity_set: str) -> str:
        """Get URL for a specific entity set"""
        return f"{self.service_url}/{entity_set}"
```

**Property Pattern:**
- `@property`: Makes method accessible like an attribute
- **URL building**: Consistent URL construction for OData endpoints
- **Encapsulation**: Hide URL construction logic

### Configuration Validation
```python
    def validate(self) -> None:
        """Validate configuration parameters"""
        if not self.service_url.startswith(('http://', 'https://')):
            raise ValueError("service_url must start with http:// or https://")
        
        # Remove trailing slash if present
        if self.service_url.endswith('/'):
            self.service_url = self.service_url.rstrip('/')
```

**Validation Patterns:**
- **Explicit validation**: Manual validation method
- **URL normalization**: Consistent URL format
- **Error handling**: Descriptive error messages
- **Side effects**: Modify configuration during validation

### ConnectorSettings Class (dynaconf wrapper)
```python
class ConnectorSettings:
    """Global connector settings using dynaconf"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.settings = Dynaconf(
            envvar_prefix="SAP_CONNECTOR",
            settings_files=[config_file] if config_file else [],
            environments=True,
            load_dotenv=True,
        )
```

**Configuration Management Concepts:**
- **dynaconf**: Advanced configuration management
- **Environment variables**: `envvar_prefix` for ENV var support
- **Multiple sources**: Files, environment, defaults
- **Environment switching**: Development, staging, production configs

### Configuration Factory Methods
```python
    def get_client_config(self) -> ClientConfig:
        """Create ClientConfig from settings"""
        return ClientConfig(**self.settings.as_dict())
    
    def get_odata_config(self) -> ODataConfig:
        """Create ODataConfig from settings"""
        return ODataConfig(
            service_url=self.settings.odata_service_url,
            username=self.settings.get('username'),
            password=self.settings.get('password'),
            client_id=self.settings.get('client_id'),
            client_secret=self.settings.get('client_secret'),
        )
```

**Factory Pattern:**
- **Object creation**: Centralized object construction
- **Configuration mapping**: Transform between different config types
- **Default handling**: Use `.get()` for optional values
- **Dictionary unpacking**: `**dict` for parameter passing

## Advanced Configuration Patterns

### Custom Validators (Pydantic)
```python
class ClientConfig(BaseModel):
    # ... other fields ...
    
    @validator('batch_size')
    def validate_batch_size(cls, v):
        if v <= 0:
            raise ValueError('batch_size must be positive')
        if v > 10000:
            raise ValueError('batch_size too large, maximum is 10000')
        return v
    
    @validator('requests_per_second')
    def validate_rate_limit(cls, v):
        if v <= 0:
            raise ValueError('requests_per_second must be positive')
        if v > 100:
            raise ValueError('rate limit too high, maximum is 100 RPS')
        return v
    
    @validator('odata_service_url')
    def validate_service_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('service_url must start with http:// or https://')
        return v.rstrip('/')  # Remove trailing slash
```

**Validator Concepts:**
- `@validator('field')`: Validates specific field
- `cls`: Class method, not instance method
- **Return value**: Must return the (possibly modified) value
- **Chaining**: Multiple validators can be applied

### Environment Variable Integration
```python
# Example .env file
ODATA_CONNECTOR_ODATA_SERVICE_URL=https://my-sap-system.com/service/
ODATA_CONNECTOR_USERNAME=myuser
ODATA_CONNECTOR_PASSWORD=mypass
ODATA_CONNECTOR_BATCH_SIZE=500
ODATA_CONNECTOR_MAX_WORKERS=3

# Usage
config = ClientConfig()  # Automatically loads from environment
```

**Environment Variable Patterns:**
- **Prefix convention**: `ODATA_CONNECTOR_` prefix for namespacing
- **Automatic loading**: Pydantic automatically reads ENV vars
- **Override hierarchy**: ENV vars override defaults

### Configuration File Support
```yaml
# config.yaml
odata_service_url: "https://services.odata.org/V4/Northwind/Northwind.svc"
batch_size: 1000
max_workers: 5
requests_per_second: 2.0
selected_modules:
  - "Categories"
  - "Products"
  - "Customers"
output_directory: "./northwind_data"

# Development environment
development:
  batch_size: 100
  max_workers: 2
  requests_per_second: 1.0

# Production environment  
production:
  batch_size: 2000
  max_workers: 10
  requests_per_second: 10.0
```

**Configuration File Patterns:**
- **YAML format**: Human-readable configuration
- **Environment sections**: Different settings per environment
- **Hierarchical structure**: Nested configuration values

### Custom Configuration Extensions
```python
class ExtendedClientConfig(ClientConfig):
    """Extended configuration with custom fields"""
    
    # Custom processing options
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    
    # Custom filtering
    global_filter: Optional[str] = Field(None, description="Global OData filter")
    exclude_entities: List[str] = Field(default_factory=list, description="Entities to exclude")
    
    # Custom authentication
    auth_token: Optional[str] = Field(None, description="Bearer token for authentication")
    auth_header_name: str = Field(default="Authorization", description="Auth header name")
    
    @validator('cache_ttl_seconds')
    def validate_cache_ttl(cls, v):
        if v < 0:
            raise ValueError('cache_ttl_seconds cannot be negative')
        return v
```

**Extension Patterns:**
- **Inheritance**: Extend base configuration classes
- **Custom fields**: Add domain-specific configuration
- **Custom validation**: Validate new fields appropriately

## Key Programming Concepts

### 1. **Data Validation**
```python
# Pydantic automatically validates:
config = ClientConfig(
    odata_service_url="invalid-url",  # Will raise ValidationError
    batch_size=-1,                    # Will raise ValidationError
    max_workers="not-a-number"        # Will raise ValidationError
)
```

### 2. **Type Safety**
```python
# Type hints provide IDE support and runtime checking
def process_config(config: ClientConfig) -> None:
    # IDE knows config.batch_size is int
    # IDE knows config.username is Optional[str]
    pass
```

### 3. **Configuration Hierarchy**
```
1. Default values (in Field definitions)
2. Configuration file values
3. Environment variable values
4. Command line arguments (handled elsewhere)
```

### 4. **Immutable Configuration**
```python
# attrs with frozen=True makes objects immutable
@attrs.define(frozen=True)
class ImmutableConfig:
    value: str = attrs.field()
    
config = ImmutableConfig("test")
# config.value = "new"  # Would raise AttributeError
```

### 5. **Configuration Factory Pattern**
```python
class ConfigFactory:
    @staticmethod
    def create_development_config() -> ClientConfig:
        return ClientConfig(
            odata_service_url="http://localhost:8080/service/",
            batch_size=100,
            max_workers=2
        )
    
    @staticmethod
    def create_production_config() -> ClientConfig:
        return ClientConfig(
            odata_service_url="https://prod-sap.company.com/service/",
            batch_size=2000,
            max_workers=10
        )
```

## Usage Examples

### Basic Configuration
```python
from config.models import ClientConfig

# Simple configuration
config = ClientConfig(
    odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
    batch_size=500,
    max_workers=3
)
```

### File-based Configuration
```python
from config.models import ConnectorSettings

# Load from file
settings = ConnectorSettings("config.yaml")
config = settings.get_client_config()
```

### Environment-based Configuration
```python
import os

# Set environment variables
os.environ["ODATA_CONNECTOR_ODATA_SERVICE_URL"] = "https://my-service.com/"
os.environ["ODATA_CONNECTOR_BATCH_SIZE"] = "1000"

# Configuration automatically loads from environment
config = ClientConfig()
```

### Validation Example
```python
try:
    config = ClientConfig(
        odata_service_url="invalid-url",
        batch_size=-1
    )
except ValidationError as e:
    print(e.json())  # Detailed validation errors
```

This file demonstrates modern Python configuration management patterns, data validation, and type safety for enterprise applications.
