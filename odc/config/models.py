"""Configuration models for SAP OData Connector"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import attrs
from dynaconf import Dynaconf


class ClientConfig(BaseModel):
    """Client configuration holding credentials, modules, and processing settings"""
    
    # OData service settings
    odata_service_url: str = Field(..., description="Full OData service URL")
    
    # Authentication (optional for public services like Northwind)
    username: Optional[str] = Field(None, description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")
    
    # Processing settings
    selected_modules: List[str] = Field(default_factory=list, description="Entity sets to process")
    total_records_limit: Optional[int] = Field(None, description="Maximum records to process")
    batch_size: int = Field(default=1000, description="Records per batch")
    max_workers: int = Field(default=5, description="Maximum concurrent workers")
    
    # Rate limiting
    requests_per_second: float = Field(default=5.0, description="Rate limit for API calls")
    max_connections: int = Field(default=50, description="Maximum HTTP connections in pool")
    
    # Local storage settings
    output_directory: str = Field(default="./output", description="Local output directory")
    raw_data_directory: str = Field(default="./output/raw", description="Raw data storage directory")
    processed_data_directory: str = Field(default="./output/processed", description="Processed data storage directory")
    
    class Config:
        env_prefix = "ODATA_CONNECTOR_"


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
    max_connections: int = attrs.field(default=50)
    
    @property
    def metadata_url(self) -> str:
        """Get the metadata endpoint URL"""
        return f"{self.service_url}/$metadata"
    
    def entity_set_url(self, entity_set: str) -> str:
        """Get URL for a specific entity set"""
        return f"{self.service_url}/{entity_set}"
    
    def validate(self) -> None:
        """Validate configuration parameters"""
        if not self.service_url.startswith(('http://', 'https://')):
            raise ValueError("service_url must start with http:// or https://")
        
        # Remove trailing slash if present
        if self.service_url.endswith('/'):
            self.service_url = self.service_url.rstrip('/')


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
