"""Google Cloud Storage implementation for raw data storage"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
import orjson
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


@dataclass
class GCSConfig:
    """Configuration for Google Cloud Storage"""
    bucket_name: str
    project_id: Optional[str] = None
    prefix: str = "sap_odata_raw"


class GCSStorage:
    """Handles raw data storage in Google Cloud Storage"""
    
    def __init__(self, config: GCSConfig):
        self.config = config
        self.client = storage.Client(project=config.project_id)
        self.bucket = self.client.bucket(config.bucket_name)
    
    async def store_raw_response(
        self,
        entity_name: str,
        command_id: str,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store raw OData response in GCS"""
        
        # Generate blob path
        timestamp = datetime.now(timezone.utc)
        blob_path = self._generate_blob_path(entity_name, command_id, timestamp)
        
        logger.debug("Storing raw data to GCS", 
                    entity_name=entity_name,
                    command_id=command_id,
                    blob_path=blob_path)
        
        try:
            # Prepare data for storage
            storage_data = {
                "entity_name": entity_name,
                "command_id": command_id,
                "timestamp": timestamp.isoformat(),
                "metadata": metadata or {},
                "raw_response": raw_data
            }
            
            # Serialize to JSON
            json_data = orjson.dumps(storage_data, option=orjson.OPT_INDENT_2)
            
            # Upload to GCS
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(
                json_data,
                content_type='application/json'
            )
            
            # Set metadata
            blob.metadata = {
                'entity_name': entity_name,
                'command_id': command_id,
                'stored_at': timestamp.isoformat()
            }
            blob.patch()
            
            logger.info("Successfully stored raw data", 
                       entity_name=entity_name,
                       blob_path=blob_path,
                       size_bytes=len(json_data))
            
            return blob_path
            
        except GoogleCloudError as e:
            logger.error("Failed to store raw data", 
                        entity_name=entity_name,
                        command_id=command_id,
                        error=str(e))
            raise
    
    def _generate_blob_path(
        self, 
        entity_name: str, 
        command_id: str, 
        timestamp: datetime
    ) -> str:
        """Generate GCS blob path for raw data"""
        
        date_path = timestamp.strftime("%Y/%m/%d")
        hour_path = timestamp.strftime("%H")
        
        # Sanitize entity name
        sanitized_entity = entity_name.replace('/', '_').replace(' ', '_')
        
        return f"{self.config.prefix}/{sanitized_entity}/{date_path}/{hour_path}/{command_id}.json"
    
    async def retrieve_raw_response(self, blob_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve raw response from GCS"""
        
        try:
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                logger.warning("Blob not found", blob_path=blob_path)
                return None
            
            # Download and parse JSON
            json_data = blob.download_as_text()
            data = orjson.loads(json_data)
            
            logger.debug("Retrieved raw data", blob_path=blob_path)
            return data
            
        except Exception as e:
            logger.error("Failed to retrieve raw data", 
                        blob_path=blob_path,
                        error=str(e))
            return None
    
    async def list_raw_files(
        self,
        entity_name: Optional[str] = None,
        date_prefix: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List raw data files in GCS"""
        
        # Build prefix for filtering
        prefix_parts = [self.config.prefix]
        
        if entity_name:
            sanitized_entity = entity_name.replace('/', '_').replace(' ', '_')
            prefix_parts.append(sanitized_entity)
        
        if date_prefix:
            prefix_parts.append(date_prefix)
        
        prefix = '/'.join(prefix_parts) + '/'
        
        try:
            blobs = self.client.list_blobs(
                self.bucket,
                prefix=prefix,
                max_results=limit
            )
            
            file_list = []
            for blob in blobs:
                file_info = {
                    'name': blob.name,
                    'size': blob.size,
                    'created': blob.time_created.isoformat() if blob.time_created else None,
                    'updated': blob.updated.isoformat() if blob.updated else None,
                    'metadata': blob.metadata or {}
                }
                file_list.append(file_info)
            
            logger.info("Listed raw files", 
                       prefix=prefix,
                       file_count=len(file_list))
            
            return file_list
            
        except Exception as e:
            logger.error("Failed to list raw files", 
                        prefix=prefix,
                        error=str(e))
            return []
    
    async def delete_old_files(self, days_old: int = 30) -> int:
        """Delete raw files older than specified days"""
        
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        try:
            blobs = self.client.list_blobs(
                self.bucket,
                prefix=f"{self.config.prefix}/"
            )
            
            deleted_count = 0
            
            for blob in blobs:
                if blob.time_created and blob.time_created < cutoff_date:
                    blob.delete()
                    deleted_count += 1
                    
                    if deleted_count % 100 == 0:
                        logger.info("Deletion progress", deleted_count=deleted_count)
            
            logger.info("Completed old file cleanup", 
                       deleted_count=deleted_count,
                       cutoff_date=cutoff_date.isoformat())
            
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to delete old files", error=str(e))
            return 0
    
    async def ensure_bucket_exists(self) -> bool:
        """Ensure GCS bucket exists"""
        
        try:
            # Try to get bucket
            self.bucket.reload()
            logger.debug("Using existing bucket", bucket_name=self.config.bucket_name)
            return True
            
        except Exception:
            # Bucket doesn't exist or no access
            logger.warning("Cannot access bucket", bucket_name=self.config.bucket_name)
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        
        try:
            blobs = self.client.list_blobs(
                self.bucket,
                prefix=f"{self.config.prefix}/"
            )
            
            total_files = 0
            total_size = 0
            entities = set()
            
            for blob in blobs:
                total_files += 1
                total_size += blob.size or 0
                
                # Extract entity name from path
                path_parts = blob.name.split('/')
                if len(path_parts) > 1:
                    entities.add(path_parts[1])
            
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'unique_entities': len(entities),
                'entities': list(entities)
            }
            
        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'unique_entities': 0,
                'entities': []
            }
