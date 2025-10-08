"""Configuration models for SAP OData Connector"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
import attrs
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ServiceType(str, Enum):
    """Supported SAP service types"""
    ODATA = "odata"
    REST = "rest"
    STREAMING = "streaming"
from dynaconf import Dynaconf
from .sap_module_mapping import SAPModuleMapping, build_sap_odata_url


class ClientConfig(BaseModel):
    """Simplified configuration for SAP Connector - credentials only"""
    
    # Service type selection
    service_type: ServiceType = Field(default=ServiceType.ODATA, description="Type of SAP service to connect to")
    
    # SAP Connection Parameters (replaces direct service_url)
    sap_server: Optional[str] = Field(None, description="SAP server hostname or IP address")
    sap_port: int = Field(default=8000, description="SAP server port (default: 8000)")
    service_name: Optional[str] = Field(None, description="SAP OData service name (e.g., 'ZMY_SERVICE_SRV') or SAP module name (e.g., 'FI', 'MM', 'ES5', 'ARIBA')")
    use_https: bool = Field(default=True, description="Use HTTPS protocol (default: True)")
    
    # Module-based configuration (alternative to service_name)
    sap_module: Optional[str] = Field(None, description="SAP module name (e.g., 'FI', 'MM', 'SD', 'ARIBA', 'CONCUR', 'ES5') - will be mapped to service_name automatically")
    
    # Authentication
    username: Optional[str] = Field(None, description="SAP username")
    password: Optional[str] = Field(None, description="SAP password")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")
    
    # SAP-specific parameters
    sap_client: Optional[str] = Field(None, description="SAP client number (e.g., '100')")
    system_id: Optional[str] = Field(None, description="SAP system ID")
    
    # Legacy support (optional - for backward compatibility)
    service_url: Optional[str] = Field(None, description="Direct SAP service URL (legacy - will be auto-constructed if not provided)")
    
    # Module/Entity selection (restored)
    selected_modules: List[str] = Field(default_factory=list, description="Specific modules/entities to process")
    
    # Storage settings (minimal)
    output_directory: str = Field(default="./output", description="Local output directory")
    
    # Processing limits
    total_records_limit: Optional[int] = Field(None, description="Global limit for total records to fetch across all entities")
    
    class Config:
        env_prefix = "SAP_CONNECTOR_"
    
    @property
    def raw_data_directory(self) -> str:
        """Default raw data directory"""
        return f"{self.output_directory}/raw"
    
    @property
    def processed_data_directory(self) -> str:
        """Default processed data directory"""
        return f"{self.output_directory}/processed"
    
    @property
    def odata_service_url(self) -> str:
        """Construct or return the SAP OData service URL"""
        if self.service_url:
            # Legacy mode - use provided URL directly
            return self.service_url
        else:
            # Determine the actual service name to use
            actual_service_name = self._resolve_service_name()
            
            # Auto-construct SAP OData URL
            url = build_sap_odata_url(
                server=self.sap_server,
                port=self.sap_port,
                service_name=actual_service_name,
                use_https=self.use_https,
                sap_client=self.sap_client
            )
            
            logger.info("Constructed SAP OData URL",
                       server=self.sap_server,
                       port=self.sap_port,
                       service_name=actual_service_name,
                       module_provided=self.sap_module,
                       url=url)
            
            return url
    
    def _resolve_service_name(self) -> str:
        """Resolve the actual OData service name from module name or direct service name"""
        # Priority 1: If sap_module is provided, map it to service name
        if self.sap_module:
            mapped_service = SAPModuleMapping.get_service_name(self.sap_module)
            if mapped_service:
                logger.info("Mapped SAP module to service name",
                           module=self.sap_module,
                           service_name=mapped_service)
                return mapped_service
            else:
                # Module not found in mapping, try to use it as-is
                logger.warning("SAP module not found in mapping, using as service name",
                             module=self.sap_module,
                             available_modules=SAPModuleMapping.get_all_modules()[:10])
                return self.sap_module
        
        # Priority 2: If service_name is provided, check if it's a module name first
        if self.service_name:
            # Check if service_name is actually a module name
            mapped_service = SAPModuleMapping.get_service_name(self.service_name)
            if mapped_service:
                logger.info("Detected module name in service_name field, mapping to service",
                           module=self.service_name,
                           service_name=mapped_service)
                return mapped_service
            else:
                # Not a module name, use as-is (direct service name)
                return self.service_name
        
        # No service name or module provided
        raise ValueError("Either service_name or sap_module must be provided")
    
    def get_entity_set_url(self, entity_set: str) -> str:
        """Get full URL for a specific entity set"""
        base_url = self.odata_service_url
        return f"{base_url}/{entity_set}"
    
    def validate(self) -> None:
        """Validate configuration parameters"""
        if self.service_url:
            # Legacy mode validation
            if not self.service_url.startswith(('http://', 'https://')):
                raise ValueError("service_url must start with http:// or https://")
            # Remove trailing slash if present
            if self.service_url.endswith('/'):
                self.service_url = self.service_url.rstrip('/')
        else:
            # New mode validation
            if not self.sap_server:
                raise ValueError("sap_server is required when service_url is not provided")
            
            # Either service_name or sap_module must be provided
            if not self.service_name and not self.sap_module:
                raise ValueError(
                    "Either service_name or sap_module must be provided when service_url is not provided. "
                    f"Supported modules: {', '.join(SAPModuleMapping.get_all_modules()[:20])}..."
                )
            
            if not isinstance(self.sap_port, int) or self.sap_port <= 0:
                raise ValueError("sap_port must be a positive integer")
            
            # Validate service name format if provided directly (not via module mapping)
            if self.service_name and not self.sap_module:
                # Check if it's a module name first
                if not SAPModuleMapping.is_valid_module(self.service_name):
                    # Not a module, validate as service name
                    if not self.service_name.replace('_', '').replace('-', '').isalnum():
                        raise ValueError("service_name should only contain alphanumeric characters, underscores, and hyphens")
    
    def get_module_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the configured SAP module"""
        module_name = self.sap_module or self.service_name
        if module_name:
            return SAPModuleMapping.get_module_info(module_name)
        return None


@attrs.define
class ODataConfig:
    """Configuration for OData service connection"""
    service_url: str = attrs.field()
    username: Optional[str] = attrs.field(default=None)
    password: Optional[str] = attrs.field(default=None)
    client_id: Optional[str] = attrs.field(default=None)
    client_secret: Optional[str] = attrs.field(default=None)
    
    # Request parameters
    timeout: int = attrs.field(default=30)
    verify_ssl: bool = attrs.field(default=True)
    max_retries: int = attrs.field(default=3)
    max_connections: int = attrs.field(default=50)  # Will be set dynamically
    
    @property
    def metadata_url(self) -> str:
        """Get the metadata endpoint URL"""
        return f"{self.service_url}/$metadata"
    
    def entity_set_url(self, entity_set: str) -> str:
        """Get URL for a specific entity set"""
        return f"{self.service_url}/{entity_set}"
    
    @classmethod
    def from_client_config(cls, client_config: 'ClientConfig') -> 'ODataConfig':
        """Create ODataConfig from ClientConfig with automatic URL construction"""
        return cls(
            service_url=client_config.odata_service_url,
            username=client_config.username,
            password=client_config.password,
            client_id=client_config.client_id,
            client_secret=client_config.client_secret,
            max_connections=50  # Default value, will be updated dynamically
        )


@attrs.define
class ExecutionConfig:
    """Runtime execution configuration - passed to get_data() method"""
    selected_entities: Optional[List[str]] = attrs.field(default=None)
    total_records_limit: Optional[int] = attrs.field(default=None)
    batch_size: int = attrs.field(default=1000)
    max_workers: int = attrs.field(default=5)
    requests_per_second: float = attrs.field(default=5.0)
    
    # Processing options
    enable_parallel_processing: bool = attrs.field(default=True)
    enable_caching: bool = attrs.field(default=False)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return attrs.asdict(self)


class ConnectorFactory:
    """Factory to create appropriate connector based on service type"""
    
    @staticmethod
    def create_connector(config: ClientConfig):
        """Create connector based on service type"""
        if config.service_type == ServiceType.ODATA:
            from ..connector import SAPODataConnector
            return SAPODataConnector(config)
        elif config.service_type == ServiceType.REST:
            # Future: REST connector - work in progress
            raise NotImplementedError("REST connector - work in progress")
        elif config.service_type == ServiceType.STREAMING:
            # Future: Streaming connector - work in progress  
            raise NotImplementedError("Streaming connector - work in progress")
        else:
            raise ValueError(f"Unsupported service type: {config.service_type}")


class ConnectorSettings:
    """Global connector settings using dynaconf"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.settings = Dynaconf(
            envvar_prefix="SAP_CONNECTOR",
            settings_files=[config_file] if config_file else [],
            environments=True,
            load_dotenv=True,
        )
    
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
