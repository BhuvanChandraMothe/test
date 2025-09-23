"""Local file storage implementation for OData connector"""

import asyncio
import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import structlog
from datetime import datetime, timezone
import orjson
import csv

from .transformer import TransformedRecord
from monitoring.metrics import get_metrics_collector

logger = structlog.get_logger(__name__)


@dataclass
class LocalStorageConfig:
    """Configuration for local file storage"""
    output_directory: str
    raw_data_directory: str
    processed_data_directory: str


class LocalFileStorage:
    """Handles local file storage for both raw and processed data"""
    
    def __init__(self, config: LocalStorageConfig):
        self.config = config
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.config.output_directory,
            self.config.raw_data_directory,
            self.config.processed_data_directory
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured directory exists", directory=directory)
    
    async def store_raw_response(
        self,
        entity_name: str,
        command_id: str,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store raw OData response as JSON file"""
        
        start_time = asyncio.get_event_loop().time()
        metrics = get_metrics_collector()
        
        # Generate file path
        timestamp = datetime.now(timezone.utc)
        file_path = self._generate_raw_file_path(entity_name, command_id, timestamp)
        
        logger.debug("Storing raw data to local file", 
                    entity_name=entity_name,
                    command_id=command_id,
                    file_path=file_path)
        
        try:
            # Prepare data for storage
            storage_data = {
                "entity_name": entity_name,
                "command_id": command_id,
                "timestamp": timestamp.isoformat(),
                "metadata": metadata or {},
                "raw_response": raw_data
            }
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON file
            with open(file_path, 'wb') as f:
                f.write(orjson.dumps(storage_data, option=orjson.OPT_INDENT_2))
            
            # Record storage metrics
            storage_time = asyncio.get_event_loop().time() - start_time
            metrics.record_storage_operation("local_file", "write", storage_time, True)
            
            logger.info("Successfully stored raw data", 
                       entity_name=entity_name,
                       file_path=file_path,
                       size_bytes=os.path.getsize(file_path),
                       storage_time_seconds=round(storage_time, 3))
            
            return file_path
            
        except Exception as e:
            # Record failed storage operation
            storage_time = asyncio.get_event_loop().time() - start_time
            metrics.record_storage_operation("local_file", "write", storage_time, False)
            
            logger.error("Failed to store raw data", 
                        entity_name=entity_name,
                        command_id=command_id,
                        error=str(e))
            raise
    
    def _generate_raw_file_path(
        self, 
        entity_name: str, 
        command_id: str, 
        timestamp: datetime
    ) -> str:
        """Generate file path for raw data"""
        
        date_path = timestamp.strftime("%Y/%m/%d")
        hour_path = timestamp.strftime("%H")
        
        # Sanitize entity name
        sanitized_entity = entity_name.replace('/', '_').replace(' ', '_')
        
        return os.path.join(
            self.config.raw_data_directory,
            sanitized_entity,
            date_path,
            hour_path,
            f"{command_id}.json"
        )
    
    async def store_processed_records(
        self, 
        entity_name: str, 
        records: List[TransformedRecord],
        format: str = "json"
    ) -> str:
        """Store processed records in specified format"""
        
        start_time = asyncio.get_event_loop().time()
        metrics = get_metrics_collector()
        
        if not records:
            logger.info("No records to store", entity_name=entity_name)
            return ""
        
        logger.info("Storing processed records", 
                   entity_name=entity_name,
                   record_count=len(records),
                   format=format)
        
        try:
            if format.lower() == "csv":
                file_path = await self._store_as_csv(entity_name, records)
            else:
                file_path = await self._store_as_json(entity_name, records)
            
            # Record successful storage operation
            storage_time = asyncio.get_event_loop().time() - start_time
            metrics.record_storage_operation("local_file", "write_processed", storage_time, True)
            
            logger.info("Successfully stored processed records", 
                       entity_name=entity_name,
                       file_path=file_path,
                       record_count=len(records),
                       storage_time_seconds=round(storage_time, 3))
            
            return file_path
            
        except Exception as e:
            # Record failed storage operation
            storage_time = asyncio.get_event_loop().time() - start_time
            metrics.record_storage_operation("local_file", "write_processed", storage_time, False)
            
            logger.error("Failed to store processed records", 
                        entity_name=entity_name,
                        error=str(e),
                        storage_time_seconds=round(storage_time, 3))
            raise
    
    async def _store_as_json(self, entity_name: str, records: List[TransformedRecord]) -> str:
        """Store records as JSON file"""
        
        timestamp = datetime.now(timezone.utc)
        sanitized_entity = entity_name.replace('/', '_').replace(' ', '_')
        
        file_path = os.path.join(
            self.config.processed_data_directory,
            f"{sanitized_entity}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # Convert records to dictionaries
        records_data = []
        for record in records:
            record_dict = {
                "entity_name": record.entity_name,
                "record_id": record.record_id,
                "transformed_at": record.transformed_at.isoformat(),
                "data": record.data,
                "metadata": record.metadata
            }
            records_data.append(record_dict)
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(orjson.dumps(records_data, option=orjson.OPT_INDENT_2))
        
        return file_path
    
    async def _store_as_csv(self, entity_name: str, records: List[TransformedRecord]) -> str:
        """Store records as CSV file"""
        
        timestamp = datetime.now(timezone.utc)
        sanitized_entity = entity_name.replace('/', '_').replace(' ', '_')
        
        file_path = os.path.join(
            self.config.processed_data_directory,
            f"{sanitized_entity}_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not records:
            return file_path
        
        # Get all unique field names from all records
        all_fields = set()
        all_fields.update(['entity_name', 'record_id', 'transformed_at'])
        
        for record in records:
            all_fields.update(record.data.keys())
        
        fieldnames = sorted(list(all_fields))
        
        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                row = {
                    'entity_name': record.entity_name,
                    'record_id': record.record_id,
                    'transformed_at': record.transformed_at.isoformat()
                }
                
                # Flatten data fields
                for field, value in record.data.items():
                    if isinstance(value, (dict, list)):
                        row[field] = json.dumps(value)
                    else:
                        row[field] = value
                
                writer.writerow(row)
        
        return file_path
    
    async def retrieve_raw_response(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve raw response from local file"""
        
        try:
            if not os.path.exists(file_path):
                logger.warning("File not found", file_path=file_path)
                return None
            
            with open(file_path, 'rb') as f:
                data = orjson.loads(f.read())
            
            logger.debug("Retrieved raw data", file_path=file_path)
            return data
            
        except Exception as e:
            logger.error("Failed to retrieve raw data", 
                        file_path=file_path,
                        error=str(e))
            return None
    
    async def list_raw_files(
        self,
        entity_name: Optional[str] = None,
        date_prefix: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List raw data files"""
        
        search_path = self.config.raw_data_directory
        
        if entity_name:
            sanitized_entity = entity_name.replace('/', '_').replace(' ', '_')
            search_path = os.path.join(search_path, sanitized_entity)
        
        if date_prefix:
            search_path = os.path.join(search_path, date_prefix.replace('-', '/'))
        
        try:
            file_list = []
            
            if os.path.exists(search_path):
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if file.endswith('.json'):
                            file_path = os.path.join(root, file)
                            stat = os.stat(file_path)
                            
                            file_info = {
                                'name': os.path.relpath(file_path, self.config.raw_data_directory),
                                'full_path': file_path,
                                'size': stat.st_size,
                                'created': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                                'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                            }
                            file_list.append(file_info)
                            
                            if len(file_list) >= limit:
                                break
            
            logger.info("Listed raw files", 
                       search_path=search_path,
                       file_count=len(file_list))
            
            return file_list
            
        except Exception as e:
            logger.error("Failed to list raw files", 
                        search_path=search_path,
                        error=str(e))
            return []
    
    async def list_processed_files(
        self,
        entity_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List processed data files"""
        
        try:
            file_list = []
            
            if os.path.exists(self.config.processed_data_directory):
                for file in os.listdir(self.config.processed_data_directory):
                    if entity_name and not file.startswith(entity_name.replace('/', '_').replace(' ', '_')):
                        continue
                    
                    file_path = os.path.join(self.config.processed_data_directory, file)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        
                        file_info = {
                            'name': file,
                            'full_path': file_path,
                            'size': stat.st_size,
                            'created': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                            'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                        }
                        file_list.append(file_info)
                        
                        if len(file_list) >= limit:
                            break
            
            logger.info("Listed processed files", 
                       entity_filter=entity_name,
                       file_count=len(file_list))
            
            return file_list
            
        except Exception as e:
            logger.error("Failed to list processed files", error=str(e))
            return []
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        
        try:
            raw_stats = await self._get_directory_stats(self.config.raw_data_directory)
            processed_stats = await self._get_directory_stats(self.config.processed_data_directory)
            
            return {
                'raw_data': raw_stats,
                'processed_data': processed_stats,
                'total_size_bytes': raw_stats['total_size'] + processed_stats['total_size'],
                'total_files': raw_stats['file_count'] + processed_stats['file_count']
            }
            
        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            return {
                'raw_data': {'file_count': 0, 'total_size': 0},
                'processed_data': {'file_count': 0, 'total_size': 0},
                'total_size_bytes': 0,
                'total_files': 0
            }
    
    async def _get_directory_stats(self, directory: str) -> Dict[str, Any]:
        """Get statistics for a directory"""
        
        total_size = 0
        file_count = 0
        entities = set()
        
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                    
                    # Extract entity name from path
                    rel_path = os.path.relpath(root, directory)
                    if rel_path != '.':
                        entity = rel_path.split(os.sep)[0]
                        entities.add(entity)
        
        return {
            'file_count': file_count,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'unique_entities': len(entities),
            'entities': list(entities)
        }
    
    async def cleanup_old_files(self, days_old: int = 30) -> int:
        """Delete files older than specified days"""
        
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        deleted_count = 0
        
        try:
            for directory in [self.config.raw_data_directory, self.config.processed_data_directory]:
                if os.path.exists(directory):
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc)
                            
                            if file_time < cutoff_date:
                                os.remove(file_path)
                                deleted_count += 1
                                
                                if deleted_count % 100 == 0:
                                    logger.info("Cleanup progress", deleted_count=deleted_count)
            
            logger.info("Completed file cleanup", 
                       deleted_count=deleted_count,
                       cutoff_date=cutoff_date.isoformat())
            
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to cleanup old files", error=str(e))
            return 0
