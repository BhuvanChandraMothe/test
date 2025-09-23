# storage/local.py - Local Storage Documentation

## Overview
The `storage/local.py` file implements the LocalFileStorage class, which handles persistent storage of OData records to the local filesystem. It supports both raw and processed data storage with configurable directory structures.

## File Structure Analysis

### Imports and Dependencies
```python
import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import structlog
from datetime import datetime

from config.models import ODataConfig
```

**Library Concepts:**
- **pathlib.Path**: Modern path handling with cross-platform compatibility
- **json**: Built-in JSON serialization for data persistence
- **asyncio**: Asynchronous file I/O operations
- **os**: Operating system interface for directory operations
- **structlog**: Structured logging for storage operations

### LocalStorageConfig Data Class
```python
@dataclass
class LocalStorageConfig:
    """Configuration for local file storage"""
    
    base_directory: str = "./output"
    raw_data_directory: str = "./output/raw"
    processed_data_directory: str = "./output/processed"
    metadata_directory: str = "./output/metadata"
    
    # File format options
    file_format: str = "json"  # json, csv, parquet
    compress: bool = False
    
    # Directory structure options
    partition_by_date: bool = True
    partition_by_entity: bool = True
    
    # File naming options
    include_timestamp: bool = True
    batch_size_in_filename: bool = False
```

**Configuration Design Patterns:**
- **Hierarchical directories**: Separate raw, processed, and metadata
- **Flexible partitioning**: Optional date and entity-based partitioning
- **Format support**: Multiple output formats (extensible)
- **Naming conventions**: Configurable filename patterns
- **Compression options**: Optional data compression

### LocalFileStorage Class Structure
```python
class LocalFileStorage:
    """Handles local file system storage for OData records"""
    
    def __init__(self, config: LocalStorageConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Ensure directories exist
        self._ensure_directories_exist()
        
        # Track files written for cleanup/reporting
        self.files_written = []
        self.total_records_written = 0
        self.total_bytes_written = 0
    
    def _ensure_directories_exist(self) -> None:
        """Create all required directories if they don't exist"""
        directories = [
            self.config.base_directory,
            self.config.raw_data_directory,
            self.config.processed_data_directory,
            self.config.metadata_directory
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.logger.debug("Directory ensured", path=directory)
```

**Storage Management Patterns:**
- **Directory initialization**: Create directory structure on startup
- **Statistics tracking**: Monitor storage operations
- **Path abstraction**: Use pathlib for cross-platform compatibility
- **Defensive programming**: Create directories if they don't exist

### Raw Data Storage
```python
async def store_raw_data(
    self, 
    entity_name: str, 
    records: List[Dict[str, Any]], 
    batch_info: Optional[Dict[str, Any]] = None
) -> str:
    """Store raw OData records to filesystem"""
    
    if not records:
        self.logger.warning("No records to store", entity=entity_name)
        return ""
    
    # Generate file path
    file_path = self._generate_file_path(
        entity_name, 
        "raw", 
        batch_info=batch_info
    )
    
    # Prepare data for storage
    storage_data = {
        "metadata": {
            "entity_name": entity_name,
            "record_count": len(records),
            "timestamp": datetime.utcnow().isoformat(),
            "batch_info": batch_info or {}
        },
        "records": records
    }
    
    # Write to file
    await self._write_json_file(file_path, storage_data)
    
    # Update statistics
    self.files_written.append(file_path)
    self.total_records_written += len(records)
    
    self.logger.info("Raw data stored", 
                    entity=entity_name,
                    file_path=file_path,
                    record_count=len(records))
    
    return file_path
```

**Raw Data Storage Concepts:**
- **Metadata wrapping**: Include entity info and timestamps with data
- **Batch tracking**: Store batch information for debugging
- **Async I/O**: Non-blocking file operations
- **Statistics updating**: Track storage metrics
- **Path generation**: Consistent file naming and organization

### Processed Data Storage
```python
async def store_processed_data(
    self, 
    entity_name: str, 
    records: List[Dict[str, Any]],
    transformation_info: Optional[Dict[str, Any]] = None
) -> str:
    """Store processed/transformed records"""
    
    file_path = self._generate_file_path(
        entity_name, 
        "processed",
        transformation_info=transformation_info
    )
    
    # Enhanced metadata for processed data
    storage_data = {
        "metadata": {
            "entity_name": entity_name,
            "record_count": len(records),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_stage": "processed",
            "transformation_info": transformation_info or {},
            "schema_version": "1.0"
        },
        "records": records
    }
    
    await self._write_json_file(file_path, storage_data)
    
    self.logger.info("Processed data stored", 
                    entity=entity_name,
                    file_path=file_path,
                    record_count=len(records))
    
    return file_path
```

**Processed Data Features:**
- **Transformation tracking**: Record what processing was applied
- **Schema versioning**: Track data format versions
- **Processing stage**: Distinguish between raw and processed data
- **Enhanced metadata**: More detailed information for processed data

### File Path Generation
```python
def _generate_file_path(
    self, 
    entity_name: str, 
    data_type: str,  # "raw" or "processed"
    batch_info: Optional[Dict[str, Any]] = None,
    transformation_info: Optional[Dict[str, Any]] = None
) -> str:
    """Generate consistent file paths based on configuration"""
    
    # Start with base directory
    if data_type == "raw":
        base_dir = Path(self.config.raw_data_directory)
    elif data_type == "processed":
        base_dir = Path(self.config.processed_data_directory)
    else:
        base_dir = Path(self.config.base_directory)
    
    # Add date partitioning if enabled
    if self.config.partition_by_date:
        today = datetime.now().strftime("%Y-%m-%d")
        base_dir = base_dir / today
    
    # Add entity partitioning if enabled
    if self.config.partition_by_entity:
        base_dir = base_dir / entity_name
    
    # Ensure directory exists
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    filename_parts = [entity_name]
    
    # Add timestamp if enabled
    if self.config.include_timestamp:
        timestamp = datetime.now().strftime("%H%M%S")
        filename_parts.append(timestamp)
    
    # Add batch info if available
    if batch_info and self.config.batch_size_in_filename:
        skip = batch_info.get('skip', 0)
        top = batch_info.get('top', 0)
        filename_parts.append(f"batch_{skip}_{top}")
    
    # Join parts and add extension
    filename = "_".join(filename_parts) + f".{self.config.file_format}"
    
    return str(base_dir / filename)
```

**Path Generation Strategy:**
- **Hierarchical organization**: Date → Entity → Files
- **Configurable partitioning**: Optional date and entity directories
- **Consistent naming**: Predictable filename patterns
- **Batch identification**: Include batch info in filenames
- **Extension handling**: Support multiple file formats

### JSON File Operations
```python
async def _write_json_file(self, file_path: str, data: Dict[str, Any]) -> None:
    """Write data to JSON file asynchronously"""
    
    def write_sync():
        """Synchronous write operation"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    # Execute in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, write_sync)
    
    # Update byte statistics
    file_size = Path(file_path).stat().st_size
    self.total_bytes_written += file_size
    
    self.logger.debug("JSON file written", 
                     file_path=file_path,
                     file_size=file_size)

async def _read_json_file(self, file_path: str) -> Dict[str, Any]:
    """Read data from JSON file asynchronously"""
    
    def read_sync():
        """Synchronous read operation"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, read_sync)
```

**Async File I/O Concepts:**
- **Thread pool execution**: Avoid blocking the event loop
- **UTF-8 encoding**: Proper Unicode handling
- **JSON formatting**: Pretty-printed output for readability
- **Default serialization**: Handle datetime and other non-JSON types
- **File size tracking**: Monitor storage usage

### Metadata Storage
```python
async def store_metadata(self, entity_name: str, schema: Dict[str, Any]) -> str:
    """Store entity metadata/schema information"""
    
    file_path = Path(self.config.metadata_directory) / f"{entity_name}_metadata.json"
    
    metadata = {
        "entity_name": entity_name,
        "schema": schema,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0"
    }
    
    await self._write_json_file(str(file_path), metadata)
    
    self.logger.info("Metadata stored", 
                    entity=entity_name,
                    file_path=str(file_path))
    
    return str(file_path)

async def load_metadata(self, entity_name: str) -> Optional[Dict[str, Any]]:
    """Load entity metadata from storage"""
    
    file_path = Path(self.config.metadata_directory) / f"{entity_name}_metadata.json"
    
    if not file_path.exists():
        return None
    
    try:
        return await self._read_json_file(str(file_path))
    except Exception as e:
        self.logger.error("Failed to load metadata", 
                         entity=entity_name,
                         error=str(e))
        return None
```

**Metadata Management:**
- **Schema persistence**: Store entity schemas for reference
- **Version tracking**: Track metadata format versions
- **Existence checking**: Handle missing metadata gracefully
- **Error handling**: Log and continue on metadata errors

### Batch Operations
```python
async def store_batch_data(
    self, 
    batch_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, str]:
    """Store multiple entities in a single operation"""
    
    file_paths = {}
    
    # Process each entity in the batch
    for entity_name, records in batch_data.items():
        if records:  # Only store if there are records
            file_path = await self.store_raw_data(entity_name, records)
            file_paths[entity_name] = file_path
    
    self.logger.info("Batch data stored", 
                    entities=list(batch_data.keys()),
                    total_files=len(file_paths))
    
    return file_paths

async def load_entity_data(
    self, 
    entity_name: str, 
    data_type: str = "raw"
) -> List[Dict[str, Any]]:
    """Load all data for a specific entity"""
    
    # Determine directory based on data type
    if data_type == "raw":
        search_dir = Path(self.config.raw_data_directory)
    else:
        search_dir = Path(self.config.processed_data_directory)
    
    # Find all files for this entity
    pattern = f"*{entity_name}*.json"
    files = list(search_dir.rglob(pattern))
    
    all_records = []
    
    for file_path in files:
        try:
            data = await self._read_json_file(str(file_path))
            records = data.get('records', [])
            all_records.extend(records)
        except Exception as e:
            self.logger.error("Failed to load file", 
                            file_path=str(file_path),
                            error=str(e))
    
    self.logger.info("Entity data loaded", 
                    entity=entity_name,
                    total_records=len(all_records),
                    files_processed=len(files))
    
    return all_records
```

**Batch Processing Features:**
- **Multi-entity storage**: Store multiple entities efficiently
- **File discovery**: Find all files for an entity using patterns
- **Recursive search**: Search subdirectories for partitioned data
- **Error resilience**: Continue loading even if some files fail
- **Aggregation**: Combine records from multiple files

### Storage Statistics and Cleanup
```python
def get_storage_statistics(self) -> Dict[str, Any]:
    """Get comprehensive storage statistics"""
    
    stats = {
        "files_written": len(self.files_written),
        "total_records_written": self.total_records_written,
        "total_bytes_written": self.total_bytes_written,
        "average_file_size": (
            self.total_bytes_written / max(len(self.files_written), 1)
        ),
        "storage_directories": {
            "raw": self.config.raw_data_directory,
            "processed": self.config.processed_data_directory,
            "metadata": self.config.metadata_directory
        }
    }
    
    # Add directory sizes if possible
    try:
        for data_type, directory in stats["storage_directories"].items():
            dir_path = Path(directory)
            if dir_path.exists():
                total_size = sum(
                    f.stat().st_size for f in dir_path.rglob('*') if f.is_file()
                )
                stats[f"{data_type}_directory_size"] = total_size
    except Exception as e:
        self.logger.warning("Could not calculate directory sizes", error=str(e))
    
    return stats

async def cleanup_old_files(self, days_to_keep: int = 7) -> int:
    """Remove files older than specified days"""
    
    cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
    files_removed = 0
    
    for directory in [self.config.raw_data_directory, 
                     self.config.processed_data_directory]:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
        
        for file_path in dir_path.rglob('*.json'):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    files_removed += 1
                    self.logger.debug("Old file removed", file_path=str(file_path))
            except Exception as e:
                self.logger.error("Failed to remove file", 
                                file_path=str(file_path),
                                error=str(e))
    
    self.logger.info("Cleanup completed", files_removed=files_removed)
    return files_removed
```

**Maintenance Operations:**
- **Statistics collection**: Comprehensive storage metrics
- **Directory size calculation**: Monitor disk usage
- **File cleanup**: Remove old files to manage disk space
- **Error handling**: Continue cleanup even if some operations fail

## Advanced Storage Concepts

### Compression Support
```python
import gzip
import pickle

class CompressedStorage(LocalFileStorage):
    """Extended storage with compression support"""
    
    async def _write_compressed_file(self, file_path: str, data: Dict[str, Any]) -> None:
        """Write compressed JSON data"""
        
        def write_sync():
            json_data = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            with gzip.open(f"{file_path}.gz", 'wt', encoding='utf-8') as f:
                f.write(json_data)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_sync)
    
    async def _read_compressed_file(self, file_path: str) -> Dict[str, Any]:
        """Read compressed JSON data"""
        
        def read_sync():
            with gzip.open(f"{file_path}.gz", 'rt', encoding='utf-8') as f:
                return json.load(f)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, read_sync)
```

### Parquet Support
```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

class ParquetStorage(LocalFileStorage):
    """Storage with Parquet format support"""
    
    async def store_as_parquet(
        self, 
        entity_name: str, 
        records: List[Dict[str, Any]]
    ) -> str:
        """Store records in Parquet format"""
        
        if not records:
            return ""
        
        file_path = self._generate_file_path(entity_name, "processed").replace('.json', '.parquet')
        
        def write_sync():
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Write to Parquet
            df.to_parquet(file_path, index=False, compression='snappy')
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_sync)
        
        return file_path
```

### Incremental Storage
```python
class IncrementalStorage(LocalFileStorage):
    """Storage with incremental/append capabilities"""
    
    async def append_records(
        self, 
        entity_name: str, 
        new_records: List[Dict[str, Any]]
    ) -> str:
        """Append records to existing file or create new one"""
        
        # Try to find existing file
        existing_file = self._find_latest_file(entity_name, "raw")
        
        if existing_file and self._file_size_under_limit(existing_file):
            # Append to existing file
            existing_data = await self._read_json_file(existing_file)
            existing_data['records'].extend(new_records)
            existing_data['metadata']['record_count'] = len(existing_data['records'])
            existing_data['metadata']['last_updated'] = datetime.utcnow().isoformat()
            
            await self._write_json_file(existing_file, existing_data)
            return existing_file
        else:
            # Create new file
            return await self.store_raw_data(entity_name, new_records)
    
    def _file_size_under_limit(self, file_path: str, limit_mb: int = 100) -> bool:
        """Check if file is under size limit"""
        try:
            size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            return size_mb < limit_mb
        except:
            return False
```

## Key Programming Concepts

### 1. **Async File I/O with Thread Pool**
```python
async def write_file_async(file_path: str, data: str):
    def write_sync():
        with open(file_path, 'w') as f:
            f.write(data)
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, write_sync)
```

### 2. **Path Generation with Configuration**
```python
def generate_path(entity: str, config: StorageConfig) -> Path:
    path = Path(config.base_directory)
    
    if config.partition_by_date:
        path = path / datetime.now().strftime("%Y-%m-%d")
    
    if config.partition_by_entity:
        path = path / entity
    
    return path / f"{entity}.json"
```

### 3. **Defensive Directory Creation**
```python
def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    # parents=True: Create parent directories
    # exist_ok=True: Don't fail if directory exists
```

### 4. **Statistics Tracking Pattern**
```python
class StorageTracker:
    def __init__(self):
        self.files_written = []
        self.bytes_written = 0
        self.records_written = 0
    
    def track_write(self, file_path: str, record_count: int):
        self.files_written.append(file_path)
        self.records_written += record_count
        self.bytes_written += Path(file_path).stat().st_size
```

## Usage Examples

### Basic Storage Operations
```python
from storage.local import LocalFileStorage, LocalStorageConfig

config = LocalStorageConfig(
    base_directory="./data",
    partition_by_date=True,
    include_timestamp=True
)

storage = LocalFileStorage(config)

# Store raw data
records = [{"id": 1, "name": "Product A"}, {"id": 2, "name": "Product B"}]
file_path = await storage.store_raw_data("Products", records)

# Store processed data
processed_records = [{"id": 1, "name": "PRODUCT A", "processed": True}]
await storage.store_processed_data("Products", processed_records)
```

### Batch Storage
```python
batch_data = {
    "Products": [{"id": 1, "name": "Product A"}],
    "Categories": [{"id": 1, "name": "Category A"}],
    "Orders": [{"id": 1, "total": 100.0}]
}

file_paths = await storage.store_batch_data(batch_data)
print(f"Stored {len(file_paths)} entity files")
```

### Data Loading
```python
# Load all data for an entity
products = await storage.load_entity_data("Products", data_type="raw")
print(f"Loaded {len(products)} product records")

# Load metadata
metadata = await storage.load_metadata("Products")
if metadata:
    print(f"Schema version: {metadata.get('version')}")
```

### Storage Management
```python
# Get statistics
stats = storage.get_storage_statistics()
print(f"Total files: {stats['files_written']}")
print(f"Total size: {stats['total_bytes_written']} bytes")

# Cleanup old files
removed = await storage.cleanup_old_files(days_to_keep=30)
print(f"Removed {removed} old files")
```

This file demonstrates enterprise-grade local storage management with flexible configuration, async operations, and comprehensive data organization capabilities.
