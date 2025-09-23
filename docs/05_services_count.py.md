# services/count.py - Count Service Documentation

## Overview
The `services/count.py` file implements the CountService class, which fetches record counts for OData entities using concurrent HTTP requests. It supports both `$count` (OData V4) and `$inlinecount` (OData V2) methods with fallback strategies.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
from typing import Dict, List, Optional, Any
import httpx
import structlog
from urllib.parse import urlencode

from config.models import ODataConfig
from services.metadata import EntitySchema
```

**Library Concepts:**
- **asyncio**: Asynchronous programming for concurrent HTTP requests
- **httpx**: Modern async HTTP client with connection pooling
- **structlog**: Structured logging with context preservation
- **urllib.parse**: URL encoding for OData query parameters

### CountService Class Structure
```python
class CountService:
    """Service to fetch entity counts from SAP OData service"""
    
    def __init__(self, odata_config: ODataConfig, max_concurrent: int = 10):
        self.odata_config = odata_config
        self.max_concurrent = max_concurrent
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = structlog.get_logger(__name__)
```

**Concurrency Control Patterns:**
- **Semaphore**: Limits concurrent HTTP requests to prevent overwhelming the server
- **Connection pooling**: httpx.AsyncClient reuses connections efficiently
- **Resource management**: HTTP client managed as instance variable
- **Structured logging**: Logger instance with context

### Async Context Manager Implementation
```python
    async def __aenter__(self):
        """Initialize HTTP client when entering context"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.odata_config.timeout),
            verify=self.odata_config.verify_ssl,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up HTTP client when exiting context"""
        if self._client:
            await self._client.aclose()
```

**Resource Management Concepts:**
- **Context manager protocol**: Ensures proper resource cleanup
- **Connection limits**: Prevents resource exhaustion
- **Keepalive connections**: Improves performance by reusing connections
- **Timeout configuration**: Uses configuration-driven timeout values

### Count Fetching with Fallback Strategy
```python
async def get_entity_counts(self, schemas: Dict[str, EntitySchema]) -> Dict[str, int]:
    """Fetch counts for all entities concurrently"""
    self.logger.info("Starting count fetching", entity_count=len(schemas))
    
    # Create tasks for concurrent execution
    tasks = []
    for entity_name in schemas.keys():
        task = asyncio.create_task(
            self._get_single_entity_count(entity_name),
            name=f"count_{entity_name}"
        )
        tasks.append((entity_name, task))
    
    # Execute all tasks concurrently and collect results
    results = {}
    for entity_name, task in tasks:
        try:
            count = await task
            results[entity_name] = count
            self.logger.info("Entity count fetched", entity=entity_name, count=count)
        except Exception as e:
            self.logger.error("Failed to fetch count", entity=entity_name, error=str(e))
            results[entity_name] = 0  # Default to 0 on error
    
    return results
```

**Concurrent Processing Patterns:**
- **Task creation**: `asyncio.create_task()` for concurrent execution
- **Task naming**: Helps with debugging and monitoring
- **Error isolation**: Individual task failures don't stop others
- **Result aggregation**: Collect all results before returning
- **Graceful degradation**: Default to 0 count on errors

### Single Entity Count with Retry Logic
```python
async def _get_single_entity_count(self, entity_name: str) -> int:
    """Get count for a single entity with fallback strategies"""
    async with self._semaphore:  # Limit concurrent requests
        try:
            # Try OData V4 $count first
            count = await self._try_count_endpoint(entity_name)
            if count is not None:
                return count
            
            # Fallback to $inlinecount for OData V2
            count = await self._try_inlinecount(entity_name)
            if count is not None:
                return count
            
            # Final fallback: sample request to check if entity exists
            sample = await self.get_entity_sample(entity_name, limit=1)
            return 1 if sample else 0
            
        except Exception as e:
            self.logger.error("All count methods failed", entity=entity_name, error=str(e))
            return 0
```

**Fallback Strategy Patterns:**
- **Semaphore protection**: Prevents too many concurrent requests
- **Progressive fallback**: Try modern method first, then legacy
- **Existence check**: Final fallback to verify entity accessibility
- **Exception handling**: Comprehensive error recovery

### OData V4 Count Method
```python
async def _try_count_endpoint(self, entity_name: str) -> Optional[int]:
    """Try OData V4 $count endpoint"""
    count_url = f"{self.odata_config.service_url}/{entity_name}/$count"
    
    try:
        auth = self._get_auth()
        response = await self._client.get(count_url, auth=auth)
        
        if response.status_code == 200:
            count_text = response.text.strip()
            if count_text.isdigit():
                return int(count_text)
        
        return None  # Not supported or invalid response
        
    except httpx.HTTPError:
        return None  # Fallback to next method
```

**OData V4 Count Concepts:**
- **Direct count endpoint**: `/{EntitySet}/$count` returns plain integer
- **Simple parsing**: Response is just a number as text
- **Status code checking**: 200 indicates success
- **Validation**: Ensure response is actually a number
- **Graceful failure**: Return None to trigger fallback

### OData V2 Inline Count Method
```python
async def _try_inlinecount(self, entity_name: str) -> Optional[int]:
    """Try OData V2 $inlinecount method"""
    params = {
        '$inlinecount': 'allpages',
        '$top': '0'  # Don't return actual data, just count
    }
    query_string = urlencode(params)
    url = f"{self.odata_config.service_url}/{entity_name}?{query_string}"
    
    try:
        auth = self._get_auth()
        response = await self._client.get(url, auth=auth)
        
        if response.status_code == 200:
            data = response.json()
            
            # OData V2 format: {"d": {"__count": "123", "results": []}}
            if 'd' in data and '__count' in data['d']:
                count_str = data['d']['__count']
                if isinstance(count_str, str) and count_str.isdigit():
                    return int(count_str)
                elif isinstance(count_str, int):
                    return count_str
        
        return None
        
    except (httpx.HTTPError, ValueError, KeyError):
        return None
```

**OData V2 Inline Count Concepts:**
- **Query parameters**: `$inlinecount=allpages` requests count in response
- **Efficiency**: `$top=0` prevents returning actual data
- **JSON parsing**: OData V2 returns structured JSON response
- **Nested structure**: Count is in `d.__count` property
- **Type flexibility**: Handle both string and integer count values

### Authentication Helper
```python
def _get_auth(self) -> Optional[tuple]:
    """Get authentication tuple if credentials are provided"""
    if self.odata_config.username and self.odata_config.password:
        return (self.odata_config.username, self.odata_config.password)
    return None
```

**Authentication Patterns:**
- **Conditional authentication**: Only add auth if credentials exist
- **HTTP Basic Auth**: Username/password tuple for httpx
- **Optional authentication**: Support both authenticated and public services
- **Configuration-driven**: Use credentials from ODataConfig

### Sample Data Fetching
```python
async def get_entity_sample(self, entity_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch sample records from an entity"""
    params = {'$top': str(limit)}
    query_string = urlencode(params)
    url = f"{self.odata_config.service_url}/{entity_name}?{query_string}"
    
    try:
        auth = self._get_auth()
        response = await self._client.get(url, auth=auth)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different OData response formats
        if 'value' in data:
            # OData V4 format
            return data['value'][:limit]
        elif 'd' in data and 'results' in data['d']:
            # OData V2 format
            return data['d']['results'][:limit]
        else:
            # Unknown format
            return []
            
    except Exception as e:
        self.logger.error("Failed to fetch sample data", entity=entity_name, error=str(e))
        return []
```

**Sample Data Concepts:**
- **Limited fetch**: Use `$top` to limit response size
- **Format detection**: Handle both OData V2 and V4 response formats
- **Data extraction**: Navigate nested JSON structure
- **Error handling**: Return empty list on failure
- **Debugging aid**: Sample data helps with troubleshooting

### Batch Count Operations
```python
async def get_counts_batch(self, entity_names: List[str], batch_size: int = 5) -> Dict[str, int]:
    """Fetch counts in batches to avoid overwhelming the server"""
    results = {}
    
    # Process entities in batches
    for i in range(0, len(entity_names), batch_size):
        batch = entity_names[i:i + batch_size]
        
        # Create tasks for this batch
        tasks = []
        for entity_name in batch:
            task = asyncio.create_task(
                self._get_single_entity_count(entity_name),
                name=f"batch_count_{entity_name}"
            )
            tasks.append((entity_name, task))
        
        # Wait for batch completion
        for entity_name, task in tasks:
            try:
                count = await task
                results[entity_name] = count
            except Exception as e:
                self.logger.error("Batch count failed", entity=entity_name, error=str(e))
                results[entity_name] = 0
        
        # Optional delay between batches
        if i + batch_size < len(entity_names):
            await asyncio.sleep(0.1)  # 100ms delay between batches
    
    return results
```

**Batch Processing Patterns:**
- **Batch sizing**: Process entities in configurable batches
- **Rate limiting**: Delay between batches to respect server limits
- **Progress tracking**: Process batches sequentially
- **Error isolation**: Batch failures don't affect other batches

## Advanced Concurrency Concepts

### Semaphore-based Rate Limiting
```python
class CountService:
    def __init__(self, odata_config: ODataConfig, max_concurrent: int = 10):
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def _get_single_entity_count(self, entity_name: str) -> int:
        async with self._semaphore:  # Acquire semaphore
            # Only max_concurrent requests run simultaneously
            return await self._make_count_request(entity_name)
        # Semaphore automatically released here
```

### Connection Pool Management
```python
# Optimal connection settings for OData services
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=20,        # Total connections
        max_keepalive_connections=10  # Reusable connections
    ),
    timeout=httpx.Timeout(30.0),   # Request timeout
    verify=True                    # SSL verification
)
```

### Error Recovery Strategies
```python
async def _get_single_entity_count(self, entity_name: str) -> int:
    """Multi-level error recovery"""
    
    # Level 1: Try modern OData V4 method
    try:
        count = await self._try_count_endpoint(entity_name)
        if count is not None:
            return count
    except httpx.HTTPError as e:
        self.logger.debug("V4 count failed", entity=entity_name, error=str(e))
    
    # Level 2: Try legacy OData V2 method
    try:
        count = await self._try_inlinecount(entity_name)
        if count is not None:
            return count
    except httpx.HTTPError as e:
        self.logger.debug("V2 count failed", entity=entity_name, error=str(e))
    
    # Level 3: Try existence check
    try:
        sample = await self.get_entity_sample(entity_name, limit=1)
        return 1 if sample else 0
    except Exception as e:
        self.logger.error("All methods failed", entity=entity_name, error=str(e))
        return 0
```

## Key Programming Concepts

### 1. **Concurrent HTTP Requests**
```python
# Sequential (slow)
counts = {}
for entity in entities:
    counts[entity] = await get_count(entity)

# Concurrent (fast)
tasks = [asyncio.create_task(get_count(entity)) for entity in entities]
counts = dict(zip(entities, await asyncio.gather(*tasks)))
```

### 2. **Semaphore-based Rate Limiting**
```python
semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

async def limited_request(url):
    async with semaphore:  # Acquire permit
        return await httpx.get(url)  # Make request
    # Permit automatically released
```

### 3. **Progressive Fallback Strategy**
```python
async def robust_operation():
    for method in [method_v4, method_v2, method_fallback]:
        try:
            result = await method()
            if result is not None:
                return result
        except Exception:
            continue  # Try next method
    return default_value  # All methods failed
```

### 4. **Context Manager Resource Management**
```python
async with CountService(config) as service:
    counts = await service.get_entity_counts(schemas)
# HTTP client automatically closed, connections cleaned up
```

## Usage Examples

### Basic Count Fetching
```python
from services.count import CountService
from config.models import ODataConfig

config = ODataConfig(
    service_url="https://services.odata.org/V4/Northwind/Northwind.svc"
)

async with CountService(config, max_concurrent=5) as service:
    counts = await service.get_entity_counts(schemas)
    
    for entity, count in counts.items():
        print(f"{entity}: {count:,} records")
```

### Sample Data Analysis
```python
async with CountService(config) as service:
    # Get sample data to understand structure
    sample = await service.get_entity_sample("Products", limit=3)
    
    for record in sample:
        print(f"Product: {record.get('ProductName')}")
        print(f"  ID: {record.get('ProductID')}")
        print(f"  Price: {record.get('UnitPrice')}")
```

### Batch Processing
```python
async with CountService(config) as service:
    large_entity_list = ["Products", "Orders", "Customers", "Categories", ...]
    
    # Process in smaller batches
    counts = await service.get_counts_batch(large_entity_list, batch_size=3)
```

### Custom Count Service
```python
class ExtendedCountService(CountService):
    async def get_filtered_count(self, entity_name: str, filter_expr: str) -> int:
        """Get count with OData filter applied"""
        params = {'$filter': filter_expr}
        if hasattr(self, '_try_count_endpoint'):
            # Try with filter on count endpoint
            count_url = f"{self.odata_config.service_url}/{entity_name}/$count"
            query_string = urlencode(params)
            url = f"{count_url}?{query_string}"
            
            response = await self._client.get(url, auth=self._get_auth())
            if response.status_code == 200:
                return int(response.text.strip())
        
        return 0
```

This file demonstrates enterprise-grade concurrent HTTP processing, error recovery strategies, and OData protocol compatibility handling.
