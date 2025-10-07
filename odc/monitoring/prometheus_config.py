"""
Prometheus configuration - separate from main connector config.
Auto-detects Pushgateway and configures metrics automatically.
"""

import os
import socket
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class PrometheusConfig:
    """
    Prometheus configuration - completely separate from ClientConfig.
    Auto-detects Pushgateway from environment variables.
    """
    
    def __init__(self):
        # Auto-detect from environment variables
        self.pushgateway_url = os.getenv('PROMETHEUS_PUSHGATEWAY_URL')
        self.job_name = os.getenv('PROMETHEUS_JOB_NAME', 'sap_odata_connector')
        self.instance_name = os.getenv('PROMETHEUS_INSTANCE_NAME', self._get_hostname())
        self.push_interval = int(os.getenv('PROMETHEUS_PUSH_INTERVAL', '10'))
        self.enabled = bool(self.pushgateway_url)  # Auto-enable if URL is set
        
        if self.enabled:
            logger.info(
                "Prometheus metrics auto-configured from environment",
                pushgateway_url=self.pushgateway_url,
                job_name=self.job_name,
                instance=self.instance_name
            )
        else:
            logger.debug("Prometheus Pushgateway not configured (set PROMETHEUS_PUSHGATEWAY_URL to enable)")
    
    def _get_hostname(self) -> str:
        """Get hostname for instance identification"""
        try:
            return socket.gethostname()
        except:
            return "unknown"
    
    @classmethod
    def from_env(cls) -> 'PrometheusConfig':
        """Create config from environment variables"""
        return cls()
    
    @classmethod
    def disabled(cls) -> 'PrometheusConfig':
        """Create a disabled config"""
        config = cls()
        config.enabled = False
        config.pushgateway_url = None
        return config


# Global Prometheus configuration
_prometheus_config: Optional[PrometheusConfig] = None


def get_prometheus_config() -> PrometheusConfig:
    """Get or create global Prometheus configuration"""
    global _prometheus_config
    if _prometheus_config is None:
        _prometheus_config = PrometheusConfig.from_env()
    return _prometheus_config


def configure_prometheus(
    pushgateway_url: Optional[str] = None,
    job_name: str = 'sap_odata_connector',
    instance_name: Optional[str] = None,
    push_interval: int = 10
) -> PrometheusConfig:
    """
    Manually configure Prometheus (optional).
    If not called, auto-detects from environment variables.
    
    Args:
        pushgateway_url: Prometheus Pushgateway URL (e.g., 'http://localhost:9091')
        job_name: Job name for metrics grouping
        instance_name: Instance identifier (auto-generated if not provided)
        push_interval: Push interval in seconds
    
    Returns:
        PrometheusConfig instance
    """
    global _prometheus_config
    
    config = PrometheusConfig()
    
    if pushgateway_url:
        config.pushgateway_url = pushgateway_url
        config.job_name = job_name
        config.instance_name = instance_name or config._get_hostname()
        config.push_interval = push_interval
        config.enabled = True
        
        logger.info(
            "Prometheus metrics manually configured",
            pushgateway_url=config.pushgateway_url,
            job_name=config.job_name,
            instance=config.instance_name
        )
    else:
        config.enabled = False
    
    _prometheus_config = config
    return config
