"""
SAP Connectors Package

Contains different connector implementations for various SAP service types.
"""

# Currently implemented
from ..connector import SAPODataConnector

# Work in progress - will be implemented later
# from .rest_connector import SAPRESTConnector
# from .streaming_connector import SAPStreamingConnector

__all__ = [
    'SAPODataConnector',
    # 'SAPRESTConnector',      # Work in progress
    # 'SAPStreamingConnector', # Work in progress
]
