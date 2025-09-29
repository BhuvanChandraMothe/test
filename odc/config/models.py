"""Configuration models for SAP OData Connector"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import attrs
from enum import Enum


class ServiceType(str, Enum):
    """Supported SAP service types"""
    ODATA = "odata"
    REST = "rest"
    STREAMING = "streaming"
from dynaconf import Dynaconf


class ClientConfig(BaseModel):
    """Simplified configuration for SAP Connector - credentials only"""
    
    # Service type selection
    service_type: ServiceType = Field(default=ServiceType.ODATA, description="Type of SAP service to connect to")
    
    # Connection settings
    service_url: str = Field(..., description="SAP service URL (OData, REST, etc.)")
    username: Optional[str] = Field(None, description="SAP username")
    password: Optional[str] = Field(None, description="SAP password")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")
    
    # SAP-specific parameters
    sap_client: Optional[str] = Field(None, description="SAP client number (e.g., '100')")
    system_id: Optional[str] = Field(None, description="SAP system ID")
    
    # Module/Entity selection (restored)
    selected_modules: List[str] = Field(default_factory=list, description="Specific modules/entities to process")
    
    # Storage settings (minimal)
    output_directory: str = Field(default="./output", description="Local output directory")
    
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
        """Backward compatibility property"""
        return self.service_url
    
    def validate(self) -> None:
        """Validate configuration parameters"""
        if not self.service_url.startswith(('http://', 'https://')):
            raise ValueError("service_url must start with http:// or https://")
        
        # Remove trailing slash if present
        if self.service_url.endswith('/'):
            self.service_url = self.service_url.rstrip('/')


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
