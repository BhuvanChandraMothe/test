"""
SAP OData Connector API with SQLite persistence

Architecture:
1. Create Config → Get config_id (stored in SQLite)
2. Create Session → Get session_id (initialized connector)
3. Execute Query → Get job_id (background job)
4. Check Job → Get results
"""
from .main import app
from .database import Database

__all__ = ['app', 'Database']
