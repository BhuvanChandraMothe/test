# workers/proxy_pool.py - Proxy Pool Documentation

## Overview
The `workers/proxy_pool.py` file implements the ProxyPool class, which manages concurrent HTTP workers for executing OData fetch commands. It provides rate limiting, circuit breaker protection, and resilient HTTP request handling.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
from typing import Dict, List, Optional, Any, Callable, Awaitable
import httpx
import structlog
from urllib.parse import urlencode

from config.models import ODataConfig
from planning.plan_generator import FetchCommand
from workers.resilience import TokenBucket, AsyncCircuitBreaker, RetryHandler
```

**Library Concepts:**
- **asyncio**: Asynchronous programming for concurrent worker management
- **httpx**: Modern async HTTP client with connection pooling
- **structlog**: Structured logging with worker context
- **urllib.parse**: URL encoding for OData query parameters
- **Custom resilience**: Rate limiting, circuit breakers, and retry logic

### ProxyPool Class Structure
```python
class ProxyPool:
    """Manages a pool of HTTP workers for concurrent OData requests"""
    
    def __init__(
        self, 
        odata_config: ODataConfig, 
        max_workers: int = 5,
        rate_limiter: Optional[TokenBucket] = None,
        circuit_breaker: Optional[AsyncCircuitBreaker] = None,
        retry_handler: Optional[RetryHandler] = None
    ):
        self.odata_config = odata_config
        self.max_workers = max_workers
        
        # Resilience components (dependency injection)
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker  
        self.retry_handler = retry_handler
        
        # Worker management
        self._client: Optional[httpx.AsyncClient] = None
        self._worker_semaphore = asyncio.Semaphore(max_workers)
        self._active_workers = 0
        
        # Statistics and monitoring
        self.stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'bytes_downloaded': 0,
            'total_records': 0
        }
        
        self.logger = structlog.get_logger(__name__)
```

**Worker Pool Design Patterns:**
- **Dependency injection**: Resilience components injected for testability
- **Semaphore-based concurrency**: Limit simultaneous HTTP requests
- **Statistics tracking**: Monitor performance and errors
- **Resource management**: HTTP client lifecycle management
- **Structured logging**: Context-aware logging

### Async Context Manager
```python
    async def __aenter__(self):
        """Initialize HTTP client and resources"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.odata_config.timeout),
            verify=self.odata_config.verify_ssl,
            limits=httpx.Limits(
                max_connections=self.max_workers * 2,  # Allow some buffer
                max_keepalive_connections=self.max_workers
            )
        )
        
        self.logger.info("ProxyPool initialized", 
                        max_workers=self.max_workers,
                        timeout=self.odata_config.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources"""
        if self._client:
            await self._client.aclose()
        
        self.logger.info("ProxyPool shutdown", 
                        requests_made=self.stats['requests_made'],
                        requests_failed=self.stats['requests_failed'])
```

**Resource Management Concepts:**
- **Connection pooling**: Reuse HTTP connections for efficiency
- **Buffer allocation**: More connections than workers for queuing
- **Graceful shutdown**: Proper resource cleanup
- **Statistics reporting**: Log final metrics on shutdown

### Command Execution Entry Point
```python
async def execute_commands(
    self, 
    commands: List[FetchCommand],
    progress_callback: Optional[Callable[[str, int], Awaitable[None]]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Execute multiple fetch commands concurrently"""
    
    self.logger.info("Starting command execution", command_count=len(commands))
    
    # Create tasks for concurrent execution
    tasks = []
    for command in commands:
        task = asyncio.create_task(
            self._execute_single_command(command, progress_callback),
            name=f"fetch_{command.entity_name}_{command.skip}"
        )
        tasks.append((command, task))
    
    # Execute all tasks and collect results
    results = {}
    for command, task in tasks:
        try:
            data = await task
            
            # Group results by entity name
            if command.entity_name not in results:
                results[command.entity_name] = []
            results[command.entity_name].extend(data)
            
        except Exception as e:
            self.logger.error("Command execution failed", 
                            entity=command.entity_name,
                            skip=command.skip,
                            error=str(e))
            # Continue with other commands
    
    self.logger.info("Command execution completed", 
                    entities_processed=len(results),
                    total_records=sum(len(records) for records in results.values()))
    
    return results
```

**Concurrent Execution Patterns:**
- **Task creation**: `asyncio.create_task()` for parallel execution
- **Task naming**: Helps with debugging and monitoring
- **Error isolation**: Individual command failures don't stop others
- **Result aggregation**: Group data by entity name
- **Progress reporting**: Optional callback for UI updates

### Single Command Execution
```python
async def _execute_single_command(
    self, 
    command: FetchCommand,
    progress_callback: Optional[Callable[[str, int], Awaitable[None]]] = None
) -> List[Dict[str, Any]]:
    """Execute a single fetch command with resilience patterns"""
    
    async with self._worker_semaphore:  # Limit concurrent workers
        self._active_workers += 1
        
        try:
            # Apply rate limiting
            if self.rate_limiter:
                await self.rate_limiter.acquire()
            
            # Execute with circuit breaker and retry protection
            if self.circuit_breaker and self.retry_handler:
                # Full resilience stack
                data = await self.circuit_breaker.call(
                    self.retry_handler.execute,
                    self._make_http_request,
                    command
                )
            elif self.circuit_breaker:
                # Circuit breaker only
                data = await self.circuit_breaker.call(self._make_http_request, command)
            elif self.retry_handler:
                # Retry only
                data = await self.retry_handler.execute(self._make_http_request, command)
            else:
                # Direct execution (bypassed for debugging)
                data = await self._make_http_request(command)
            
            # Update statistics
            self.stats['requests_made'] += 1
            self.stats['total_records'] += len(data)
            
            # Report progress
            if progress_callback:
                await progress_callback(command.entity_name, len(data))
            
            return data
            
        except Exception as e:
            self.stats['requests_failed'] += 1
            self.logger.error("Command execution failed", 
                            entity=command.entity_name,
                            error=str(e))
            raise
        finally:
            self._active_workers -= 1
```

**Resilience Pattern Integration:**
- **Semaphore protection**: Limit concurrent workers
- **Rate limiting**: Prevent overwhelming the server
- **Circuit breaker**: Stop requests when service is failing
- **Retry logic**: Automatically retry transient failures
- **Statistics tracking**: Monitor success/failure rates
- **Progress callbacks**: Real-time progress updates

### HTTP Request Implementation
```python
async def _make_http_request(self, command: FetchCommand) -> List[Dict[str, Any]]:
    """Make the actual HTTP request to OData service"""
    
    # Build OData query parameters
    params = {
        '$skip': str(command.skip),
        '$top': str(command.top)
    }
    
    # Add format parameter for JSON response
    params['$format'] = 'json'
    
    # Build complete URL
    base_url = f"{self.odata_config.service_url}/{command.entity_set}"
    query_string = urlencode(params)
    url = f"{base_url}?{query_string}"
    
    # Prepare authentication
    auth = None
    if self.odata_config.username and self.odata_config.password:
        auth = (self.odata_config.username, self.odata_config.password)
    
    try:
        self.logger.debug("Making HTTP request", 
                         entity=command.entity_name,
                         url=url,
                         skip=command.skip,
                         top=command.top)
        
        response = await self._client.get(url, auth=auth)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Extract records from OData response format
        records = self._extract_records(data)
        
        # Update byte statistics
        self.stats['bytes_downloaded'] += len(response.content)
        
        self.logger.debug("HTTP request completed", 
                         entity=command.entity_name,
                         records_fetched=len(records),
                         response_size=len(response.content))
        
        return records
        
    except httpx.HTTPError as e:
        self.logger.error("HTTP request failed", 
                         entity=command.entity_name,
                         url=url,
                         error=str(e))
        raise
    except ValueError as e:
        self.logger.error("JSON parsing failed", 
                         entity=command.entity_name,
                         error=str(e))
        raise
```

**HTTP Request Concepts:**
- **OData query parameters**: `$skip`, `$top`, `$format` for pagination and format
- **URL construction**: Build complete OData query URL
- **Authentication handling**: Optional HTTP Basic Auth
- **Response parsing**: Extract JSON data from HTTP response
- **Error handling**: Distinguish HTTP errors from parsing errors
- **Metrics collection**: Track bytes downloaded and response sizes

### OData Response Parsing
```python
def _extract_records(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract record list from OData JSON response"""
    
    # OData V4 format: {"@odata.context": "...", "value": [...]}
    if 'value' in response_data:
        return response_data['value']
    
    # OData V2 format: {"d": {"results": [...]}}
    elif 'd' in response_data and 'results' in response_data['d']:
        return response_data['d']['results']
    
    # Single record (not an array)
    elif 'd' in response_data and isinstance(response_data['d'], dict):
        return [response_data['d']]
    
    # Unknown format - return as-is and let caller handle
    else:
        self.logger.warning("Unknown OData response format", 
                           response_keys=list(response_data.keys()))
        return [response_data] if isinstance(response_data, dict) else []
```

**OData Format Compatibility:**
- **Version detection**: Handle both OData V2 and V4 response formats
- **Nested structure**: Navigate JSON hierarchy to find actual data
- **Single record handling**: Convert single records to list format
- **Graceful fallback**: Handle unknown formats without crashing
- **Logging**: Warn about unexpected response formats

### Worker Pool Statistics
```python
def get_statistics(self) -> Dict[str, Any]:
    """Get current worker pool statistics"""
    return {
        'active_workers': self._active_workers,
        'max_workers': self.max_workers,
        'requests_made': self.stats['requests_made'],
        'requests_failed': self.stats['requests_failed'],
        'success_rate': (
            (self.stats['requests_made'] - self.stats['requests_failed']) / 
            max(self.stats['requests_made'], 1)
        ),
        'bytes_downloaded': self.stats['bytes_downloaded'],
        'total_records': self.stats['total_records'],
        'avg_records_per_request': (
            self.stats['total_records'] / max(self.stats['requests_made'], 1)
        )
    }

def reset_statistics(self) -> None:
    """Reset all statistics counters"""
    self.stats = {
        'requests_made': 0,
        'requests_failed': 0,
        'bytes_downloaded': 0,
        'total_records': 0
    }
```

**Monitoring and Metrics:**
- **Real-time statistics**: Track active workers and performance
- **Success rate calculation**: Monitor reliability
- **Throughput metrics**: Records per request, bytes downloaded
- **Reset capability**: Clear statistics for new test runs

### Advanced Worker Management
```python
async def scale_workers(self, new_max_workers: int) -> None:
    """Dynamically adjust the number of workers"""
    if new_max_workers <= 0:
        raise ValueError("max_workers must be positive")
    
    old_max = self.max_workers
    self.max_workers = new_max_workers
    
    # Update semaphore (this is tricky - might need to recreate)
    self._worker_semaphore = asyncio.Semaphore(new_max_workers)
    
    self.logger.info("Worker pool scaled", 
                    old_max=old_max, 
                    new_max=new_max_workers)

async def wait_for_completion(self) -> None:
    """Wait for all active workers to complete"""
    while self._active_workers > 0:
        await asyncio.sleep(0.1)
    
    self.logger.info("All workers completed")

def is_idle(self) -> bool:
    """Check if worker pool is idle (no active workers)"""
    return self._active_workers == 0
```

**Dynamic Management:**
- **Runtime scaling**: Adjust worker count during execution
- **Completion waiting**: Wait for all workers to finish
- **Idle detection**: Check if pool is ready for shutdown
- **State monitoring**: Track worker pool state

## Advanced Concurrency Concepts

### Semaphore-based Worker Limiting
```python
class ProxyPool:
    def __init__(self, max_workers: int = 5):
        self._worker_semaphore = asyncio.Semaphore(max_workers)
    
    async def _execute_single_command(self, command):
        async with self._worker_semaphore:  # Acquire worker slot
            # Only max_workers can execute simultaneously
            return await self._make_http_request(command)
        # Worker slot automatically released
```

### Connection Pool Optimization
```python
# Optimal settings for OData services
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=max_workers * 2,      # Buffer for queued requests
        max_keepalive_connections=max_workers  # Reuse connections
    ),
    timeout=httpx.Timeout(
        connect=10.0,    # Connection timeout
        read=30.0,       # Read timeout
        write=10.0,      # Write timeout
        pool=5.0         # Pool acquisition timeout
    )
)
```

### Resilience Pattern Composition
```python
async def _execute_with_full_resilience(self, command):
    """Execute command with all resilience patterns"""
    
    # Layer 1: Rate limiting
    await self.rate_limiter.acquire()
    
    # Layer 2: Circuit breaker
    if self.circuit_breaker.is_open():
        raise CircuitBreakerError("Circuit breaker is open")
    
    # Layer 3: Retry with exponential backoff
    for attempt in range(self.max_retries):
        try:
            return await self._make_http_request(command)
        except TransientError as e:
            if attempt < self.max_retries - 1:
                delay = 2 ** attempt  # Exponential backoff
                await asyncio.sleep(delay)
                continue
            raise
```

### Error Classification and Handling
```python
def classify_error(self, error: Exception) -> str:
    """Classify errors for appropriate handling"""
    
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    elif isinstance(error, httpx.ConnectError):
        return "connection"
    elif isinstance(error, httpx.HTTPStatusError):
        if error.response.status_code >= 500:
            return "server_error"  # Retryable
        elif error.response.status_code == 429:
            return "rate_limited"  # Retryable with backoff
        else:
            return "client_error"  # Not retryable
    else:
        return "unknown"

async def handle_error(self, error: Exception, command: FetchCommand):
    """Handle errors based on classification"""
    
    error_type = self.classify_error(error)
    
    if error_type in ["timeout", "connection", "server_error"]:
        # Retryable errors
        raise RetryableError(str(error))
    elif error_type == "rate_limited":
        # Rate limited - wait and retry
        await asyncio.sleep(60)  # Wait 1 minute
        raise RetryableError(str(error))
    else:
        # Permanent errors
        raise PermanentError(str(error))
```

## Key Programming Concepts

### 1. **Async Context Manager Pattern**
```python
async with ProxyPool(config, max_workers=5) as pool:
    results = await pool.execute_commands(commands)
# HTTP client automatically closed, resources cleaned up
```

### 2. **Semaphore-based Concurrency Control**
```python
semaphore = asyncio.Semaphore(5)  # Max 5 concurrent operations

async def worker():
    async with semaphore:  # Acquire permit
        await do_work()    # Do work
    # Permit automatically released
```

### 3. **Task Management with Error Isolation**
```python
tasks = [asyncio.create_task(process(item)) for item in items]

results = []
for task in tasks:
    try:
        result = await task
        results.append(result)
    except Exception as e:
        logger.error("Task failed", error=str(e))
        # Continue with other tasks
```

### 4. **Statistics and Monitoring**
```python
class WorkerPool:
    def __init__(self):
        self.stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'bytes_downloaded': 0
        }
    
    async def make_request(self, url):
        try:
            response = await httpx.get(url)
            self.stats['requests_made'] += 1
            self.stats['bytes_downloaded'] += len(response.content)
            return response
        except Exception:
            self.stats['requests_failed'] += 1
            raise
```

## Usage Examples

### Basic Worker Pool Usage
```python
from workers.proxy_pool import ProxyPool
from config.models import ODataConfig

config = ODataConfig(
    service_url="https://services.odata.org/V4/Northwind/Northwind.svc"
)

async with ProxyPool(config, max_workers=3) as pool:
    results = await pool.execute_commands(fetch_commands)
    
    stats = pool.get_statistics()
    print(f"Processed {stats['total_records']} records")
    print(f"Success rate: {stats['success_rate']:.2%}")
```

### Worker Pool with Resilience
```python
from workers.resilience import TokenBucket, AsyncCircuitBreaker, RetryHandler

# Create resilience components
rate_limiter = TokenBucket(rate=5.0, capacity=10)
circuit_breaker = AsyncCircuitBreaker(failure_threshold=5, timeout=60)
retry_handler = RetryHandler(max_retries=3, backoff_factor=2.0)

async with ProxyPool(
    config, 
    max_workers=5,
    rate_limiter=rate_limiter,
    circuit_breaker=circuit_breaker,
    retry_handler=retry_handler
) as pool:
    results = await pool.execute_commands(commands)
```

### Progress Monitoring
```python
async def progress_callback(entity_name: str, records_fetched: int):
    print(f"Fetched {records_fetched} records from {entity_name}")

async with ProxyPool(config) as pool:
    results = await pool.execute_commands(commands, progress_callback)
```

### Custom Worker Pool
```python
class CustomProxyPool(ProxyPool):
    async def _make_http_request(self, command: FetchCommand) -> List[Dict[str, Any]]:
        """Custom request handling with additional headers"""
        
        # Add custom headers
        headers = {
            'User-Agent': 'SAP-OData-Connector/1.0',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Build URL
        url = self._build_url(command)
        auth = self._get_auth()
        
        response = await self._client.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        
        return self._extract_records(response.json())
```

This file demonstrates enterprise-grade concurrent HTTP processing with comprehensive resilience patterns, error handling, and monitoring capabilities.
