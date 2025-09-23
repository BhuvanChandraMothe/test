# SAP OData Connector - Complete Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture & Core Concepts](#architecture--core-concepts)
3. [Component Breakdown](#component-breakdown)
4. [Configuration & Input Parameters](#configuration--input-parameters)
5. [Usage Examples](#usage-examples)
6. [Customization Guide](#customization-guide)
7. [Troubleshooting](#troubleshooting)

## Overview

The SAP OData Connector is an asynchronous Python framework designed to extract, transform, and store data from SAP OData services. It implements enterprise-grade patterns including rate limiting, circuit breakers, retry mechanisms, and parallel processing.

### Key Features
- **Async/Await Architecture**: Non-blocking I/O for high performance
- **Resilience Patterns**: Circuit breakers, retries, rate limiting
- **Metadata Discovery**: Automatic schema detection and relationship mapping
- **Parallel Processing**: Concurrent workers with dependency management
- **Data Transformation**: Structured data processing and storage
- **Monitoring & Metrics**: Built-in performance tracking and alerting

## Architecture & Core Concepts

### 1. Async Programming Model
```python
# The entire connector is built on Python's asyncio
async def main():
    connector = SAPODataConnector(config)
    await connector.initialize()  # Non-blocking initialization
    stats = await connector.run()  # Parallel data processing
```

**Concepts Used:**
- **Event Loop**: Single-threaded concurrency model
- **Coroutines**: Functions that can be paused and resumed
- **Tasks**: Concurrent execution units
- **Context Managers**: Resource management with `async with`

### 2. Dependency Injection Pattern
```python
class SAPODataConnector:
    def __init__(self, config: ClientConfig):
        self.sap_config = self._create_sap_config()  # Transform config
        self.metadata_service = MetadataService(self.sap_config)  # Inject dependencies
        self.count_service = CountService(self.sap_config)
```

**Why This Matters:**
- Loose coupling between components
- Easy testing with mock objects
- Configuration centralization

### 3. Producer-Consumer Pattern
```python
# Producer: Plan Generator creates commands
commands = self.plan_generator.get_initial_commands()

# Consumer: Proxy Pool processes commands
await self.proxy_pool.add_commands(commands)
```

## Component Breakdown

### 1. Configuration Layer (`config/models.py`)

#### ClientConfig Class
```python
class ClientConfig(BaseModel):
    odata_service_url: str = Field(..., description="Full OData service URL")
    username: Optional[str] = Field(None, description="Username for authentication")
    # ... more fields
```

**Line-by-Line Explanation:**
- `BaseModel`: Inherits from Pydantic for data validation
- `Field(...)`: Required field with validation
- `Field(None)`: Optional field with default None
- `Field(default=1000)`: Optional field with custom default

**Input Customization:**
```python
config = ClientConfig(
    odata_service_url="https://your-sap-system.com/sap/opu/odata/sap/SERVICE_NAME/",
    username="your_username",
    password="your_password",
    batch_size=500,  # Reduce for slower systems
    max_workers=3,   # Increase for faster systems
    requests_per_second=2.0  # Adjust based on SAP system limits
)
```

#### ODataConfig Class
```python
@attrs.define
class ODataConfig:
    service_url: str = attrs.field()
    timeout: int = attrs.field(default=30)
```

**Concepts:**
- `@attrs.define`: Alternative to dataclasses with more features
- `attrs.field()`: Field definition with validation and defaults

### 2. Metadata Service (`services/metadata.py`)

#### Core Functionality
```python
async def fetch_metadata(self) -> Dict[str, EntitySchema]:
    response = await self._client.get(self.odata_config.metadata_url, auth=auth)
    edmx_content = response.text
    await self._parse_edmx(edmx_content)
    return self.schemas
```

**Step-by-Step Process:**
1. **HTTP Request**: Fetch EDMX metadata from `$metadata` endpoint
2. **XML Parsing**: Parse OData schema using ElementTree
3. **Schema Extraction**: Convert XML to Python objects
4. **Relationship Mapping**: Build entity relationships

#### XML Namespace Handling
```python
namespaces = {
    'edmx': 'http://docs.oasis-open.org/odata/ns/edmx',
    'edm': 'http://docs.oasis-open.org/odata/ns/edm'
}
entity_types = root.findall('.//edm:EntityType', namespaces)
```

**Why Namespaces Matter:**
- OData v4 uses OASIS namespaces (different from v2)
- XML parsing requires explicit namespace declarations
- `.//` means "find anywhere in the document tree"

#### EntitySet vs EntityType Mapping
```python
# EntitySet: The queryable collection (e.g., "Categories")
# EntityType: The schema definition (e.g., "Category")
for entity_set in entity_sets:
    set_name = entity_set.get('Name')        # "Categories"
    type_name = entity_set.get('EntityType') # "NorthwindModel.Category"
    type_name = type_name.split('.')[-1]     # "Category"
    entity_set_mapping[set_name] = type_name
```

**Customization Options:**
```python
# To add custom metadata parsing:
class CustomMetadataService(MetadataService):
    async def _parse_custom_annotations(self, root):
        # Parse SAP-specific annotations
        annotations = root.findall('.//edm:Annotation', self.namespaces)
        for annotation in annotations:
            # Custom logic here
            pass
```

### 3. Count Service (`services/count.py`)

#### Concurrent Count Fetching
```python
async def get_entity_counts(self, entity_sets: List[str]) -> Dict[str, int]:
    tasks = []
    for entity_set in entity_sets:
        task = asyncio.create_task(
            self._get_single_entity_count(entity_set),
            name=f"count_{entity_set}"
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Concepts Explained:**
- `asyncio.create_task()`: Schedules coroutine for execution
- `asyncio.gather()`: Waits for all tasks to complete
- `return_exceptions=True`: Don't fail if one task fails

#### Fallback Strategy
```python
async def _get_single_entity_count(self, entity_set: str) -> int:
    try:
        # Try $count endpoint (OData v4)
        count_url = f"{self.odata_config.entity_set_url(entity_set)}/$count"
        response = await self._client.get(count_url)
        if response.status_code == 200:
            return int(response.text.strip())
        elif response.status_code == 404:
            # Fallback to $inlinecount (OData v2)
            return await self._get_count_with_inlinecount(entity_set)
```

**Input Customization:**
```python
# To modify count behavior:
class CustomCountService(CountService):
    async def _get_single_entity_count(self, entity_set: str) -> int:
        # Add custom filtering
        filter_clause = "$filter=Status eq 'Active'"
        count_url = f"{self.odata_config.entity_set_url(entity_set)}/$count?{filter_clause}"
        # ... rest of logic
```

### 4. Plan Generator (`planning/plan_generator.py`)

#### Command Generation Logic
```python
def create_execution_plan(self, entity_counts: Dict[str, int], 
                         processing_order: List[List[str]]) -> Dict[str, EntityPlan]:
    for level_idx, level_entities in enumerate(processing_order):
        for entity in level_entities:
            record_count = entity_counts[entity]
            if record_count == 0:
                continue  # Skip empty entities
            
            total_pages = math.ceil(record_count / self.batch_size)
            plan = EntityPlan(entity_name=entity, total_records=record_count, 
                            page_size=self.batch_size, total_pages=total_pages)
```

**Key Concepts:**
- **Pagination**: Large datasets split into manageable chunks
- **Dependency Levels**: Process parent entities before children
- **Priority Assignment**: High-priority entities processed first

#### FetchCommand Structure
```python
@dataclass
class FetchCommand:
    command_id: str              # Unique identifier
    command_type: CommandType    # FETCH_PAGE, COUNT_RECORDS, etc.
    entity_set: str             # Target entity (e.g., "Categories")
    skip: int = 0               # OData $skip parameter
    top: int = 1000             # OData $top parameter (page size)
    filter_clause: Optional[str] = None  # OData $filter
```

**Customization Examples:**
```python
# Custom filtering
command = FetchCommand(
    command_id="active_products",
    command_type=CommandType.FETCH_PAGE,
    entity_set="Products",
    filter_clause="Discontinued eq false",
    select_clause="ProductID,ProductName,UnitPrice"
)

# Custom ordering
command.orderby_clause = "ProductName asc"
```

### 5. Proxy Pool (`workers/proxy_pool.py`)

#### Worker Pool Pattern
```python
class ProxyPool:
    def __init__(self, odata_config: ODataConfig, max_workers: int = 5):
        self.max_workers = max_workers
        self.workers: List[ProxyWorker] = []
        self.command_queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(max_workers)
```

**Concepts:**
- **Semaphore**: Limits concurrent operations
- **Queue**: Thread-safe command distribution
- **Worker Pool**: Reusable execution units

#### Request Execution Flow
```python
async def execute_command(self, command: FetchCommand) -> ProxyResult:
    async with self.semaphore:  # Acquire worker slot
        await self.resilience.token_bucket.acquire()  # Rate limiting
        result = await self._make_http_request(command)  # Execute
        return result
```

**Rate Limiting Implementation:**
```python
class TokenBucket:
    def __init__(self, config: TokenBucketConfig):
        self.rate_limiter = AsyncLimiter(
            max_rate=config.max_rate,      # Requests per second
            time_period=config.time_period  # Time window
        )
    
    async def acquire(self) -> None:
        await self.rate_limiter.acquire()  # Blocks until token available
```

### 6. Resilience Patterns (`workers/resilience.py`)

#### Circuit Breaker Pattern
```python
class AsyncCircuitBreaker:
    async def call(self, func: Callable, *args, **kwargs):
        if self._circuit_breaker.current_state == 'open':
            raise CircuitBreakerError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._circuit_breaker._failure_count = 0  # Reset on success
            return result
        except Exception as e:
            self._circuit_breaker._failure_count += 1
            if self._circuit_breaker._failure_count >= self._circuit_breaker._failure_threshold:
                self._circuit_breaker._state = 'open'
            raise
```

**States Explained:**
- **Closed**: Normal operation, requests pass through
- **Open**: Failures exceeded threshold, requests blocked
- **Half-Open**: Testing if service recovered

#### Retry Handler
```python
class RetryHandler:
    def __init__(self, config: RetryConfig):
        self.retryer = Retrying(
            stop=stop_after_attempt(config.max_attempts),
            wait=wait_exponential(multiplier=config.multiplier, min=config.min_wait, max=config.max_wait),
            retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
        )
```

**Exponential Backoff:**
- First retry: 1 second
- Second retry: 2 seconds  
- Third retry: 4 seconds
- Maximum: 60 seconds

### 7. Storage Layer (`storage/local_storage.py`)

#### File Organization
```python
async def store_raw_response(self, entity_name: str, response_data: Dict[str, Any], 
                           batch_info: Dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc)
    date_path = timestamp.strftime("%Y/%m/%d/%H")
    filename = f"{entity_name}_page_{batch_info['page_number']}.json"
    file_path = Path(self.config.raw_data_directory) / entity_name / date_path / filename
```

**Directory Structure:**
```
test_output/
├── raw/
│   ├── Categories/
│   │   └── 2025/09/17/12/
│   │       ├── Categories_page_1.json
│   │       └── Categories_page_2.json
│   └── Products/
└── processed/
    ├── Categories_20250917_122430.json
    └── Products_20250917_122431.json
```

#### Data Transformation
```python
class DataTransformer:
    async def transform_record(self, entity_name: str, raw_record: Dict[str, Any]) -> TransformedRecord:
        # Extract primary key
        primary_key = self._extract_primary_key(entity_name, raw_record)
        
        # Generate unique record ID
        record_id = f"{entity_name}_{primary_key}"
        
        return TransformedRecord(
            entity_name=entity_name,
            record_id=record_id,
            transformed_at=datetime.now(timezone.utc),
            data=raw_record
        )
```

## Configuration & Input Parameters

### Basic Configuration
```python
config = ClientConfig(
    # Required: OData service endpoint
    odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
    
    # Authentication (optional for public services)
    username="your_username",
    password="your_password",
    client_id="oauth_client_id",        # For OAuth2
    client_secret="oauth_client_secret", # For OAuth2
    
    # Processing limits
    selected_modules=[],                 # Empty = all entities
    total_records_limit=10000,          # Max records across all entities
    batch_size=1000,                    # Records per API call
    max_workers=5,                      # Concurrent workers
    
    # Rate limiting
    requests_per_second=5.0,            # API calls per second
    
    # Storage paths
    output_directory="./output",
    raw_data_directory="./output/raw",
    processed_data_directory="./output/processed"
)
```

### Advanced Configuration Options

#### Custom Entity Selection
```python
config = ClientConfig(
    # ... other settings
    selected_modules=["Categories", "Products", "Customers"],  # Only these entities
    total_records_limit=50000,
    batch_size=500  # Smaller batches for complex entities
)
```

#### Performance Tuning
```python
# High-performance configuration
config = ClientConfig(
    # ... other settings
    max_workers=10,              # More concurrent workers
    requests_per_second=10.0,    # Higher rate limit
    batch_size=2000             # Larger batches
)

# Conservative configuration (for slower SAP systems)
config = ClientConfig(
    # ... other settings
    max_workers=2,               # Fewer workers
    requests_per_second=1.0,     # Lower rate limit
    batch_size=100              # Smaller batches
)
```

## Usage Examples

### Basic Usage
```python
import asyncio
from config.models import ClientConfig
from connector import SAPODataConnector

async def main():
    # 1. Create configuration
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        total_records_limit=1000,
        batch_size=100,
        max_workers=3
    )
    
    # 2. Initialize connector
    connector = SAPODataConnector(config)
    
    # 3. Set up progress callback (optional)
    def progress_callback(progress):
        print(f"Progress: {progress['completed_entities']} entities, "
              f"{progress['records_processed']} records")
    
    connector.on_progress_update = progress_callback
    
    try:
        # 4. Initialize services
        await connector.initialize()
        
        # 5. Run data extraction
        stats = await connector.run()
        
        # 6. Print results
        print(f"Completed in {stats.duration_seconds:.2f}s")
        print(f"Entities: {stats.entities_processed}")
        print(f"Records: {stats.records_processed}")
        
    finally:
        # 7. Cleanup
        if connector.proxy_pool:
            await connector.proxy_pool.stop()

# Run the connector
asyncio.run(main())
```

### Custom Entity Processing
```python
async def process_specific_entities():
    config = ClientConfig(
        odata_service_url="https://your-sap-system.com/sap/opu/odata/sap/SERVICE/",
        username="username",
        password="password",
        selected_modules=["CUSTOMER", "SALES_ORDER", "SALES_ORDER_ITEM"],
        batch_size=500
    )
    
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # Process only selected entities
    stats = await connector.run(selected_entities=["CUSTOMER", "SALES_ORDER"])
    
    return stats
```

### Error Handling
```python
async def robust_extraction():
    config = ClientConfig(
        odata_service_url="https://your-sap-system.com/service/",
        max_workers=3,
        requests_per_second=2.0
    )
    
    connector = SAPODataConnector(config)
    
    try:
        await connector.initialize()
        stats = await connector.run()
        
        if stats.commands_failed > 0:
            print(f"Warning: {stats.commands_failed} commands failed")
            # Check dead letter queue for failed commands
            failed_commands = connector.dead_letter_queue.get_failed_commands()
            for cmd in failed_commands:
                print(f"Failed: {cmd.entity_set} - {cmd.error}")
        
        return stats
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        # Implement custom error handling
        raise
    
    finally:
        await connector.cleanup()
```

## Customization Guide

### 1. Custom Authentication
```python
class CustomODataConfig(ODataConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_token = self._get_custom_token()
    
    def _get_custom_token(self):
        # Implement custom authentication logic
        return "Bearer your_custom_token"

# Use custom config
config = ClientConfig(...)
connector = SAPODataConnector(config)
connector.sap_config = CustomODataConfig(
    service_url=config.odata_service_url,
    # ... other parameters
)
```

### 2. Custom Data Transformation
```python
class CustomDataTransformer(DataTransformer):
    async def transform_record(self, entity_name: str, raw_record: Dict[str, Any]) -> TransformedRecord:
        # Apply custom business logic
        if entity_name == "Products":
            # Add calculated fields
            raw_record["TotalValue"] = raw_record.get("UnitPrice", 0) * raw_record.get("UnitsInStock", 0)
            
            # Format dates
            if "CreatedDate" in raw_record:
                raw_record["CreatedDate"] = self._format_sap_date(raw_record["CreatedDate"])
        
        return await super().transform_record(entity_name, raw_record)
    
    def _format_sap_date(self, sap_date_string: str) -> str:
        # Convert SAP date format to ISO format
        # Implementation depends on SAP date format
        return formatted_date

# Use custom transformer
connector = SAPODataConnector(config)
await connector.initialize()
connector.transformer = CustomDataTransformer(connector.metadata_service.schemas)
```

### 3. Custom Storage Backend
```python
class DatabaseStorage:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    async def store_raw_response(self, entity_name: str, response_data: Dict, batch_info: Dict) -> str:
        # Store in database instead of files
        async with self.get_connection() as conn:
            await conn.execute(
                "INSERT INTO raw_data (entity_name, data, batch_info) VALUES (?, ?, ?)",
                (entity_name, json.dumps(response_data), json.dumps(batch_info))
            )
        return f"db_record_{batch_info['page_number']}"
    
    async def store_transformed_record(self, record: TransformedRecord) -> str:
        # Store transformed data
        async with self.get_connection() as conn:
            await conn.execute(
                "INSERT INTO processed_data (entity_name, record_id, data) VALUES (?, ?, ?)",
                (record.entity_name, record.record_id, json.dumps(record.data))
            )
        return record.record_id

# Use custom storage
connector = SAPODataConnector(config)
await connector.initialize()
connector.local_storage = DatabaseStorage("postgresql://user:pass@localhost/db")
```

### 4. Custom Filtering and Selection
```python
class FilteredPlanGenerator(PlanGenerator):
    def create_execution_plan(self, entity_counts: Dict[str, int], 
                            processing_order: List[List[str]], 
                            selected_entities: Optional[List[str]] = None) -> Dict[str, EntityPlan]:
        
        # Apply custom filtering logic
        filtered_counts = {}
        for entity, count in entity_counts.items():
            if entity == "LARGE_TABLE" and count > 1000000:
                # Skip very large tables
                continue
            elif entity.startswith("TEMP_"):
                # Skip temporary tables
                continue
            else:
                filtered_counts[entity] = count
        
        return super().create_execution_plan(filtered_counts, processing_order, selected_entities)

# Use custom plan generator
connector = SAPODataConnector(config)
await connector.initialize()
connector.plan_generator = FilteredPlanGenerator(
    batch_size=config.batch_size,
    max_concurrent_entities=config.max_workers
)
```

### 5. Custom Monitoring and Alerts
```python
class CustomMetricsCollector(MetricsCollector):
    def record_request_duration(self, entity_name: str, duration: float):
        super().record_request_duration(entity_name, duration)
        
        # Send to custom monitoring system
        if duration > 30.0:  # Alert on slow requests
            self.send_alert(f"Slow request detected: {entity_name} took {duration}s")
    
    def send_alert(self, message: str):
        # Implement custom alerting (email, Slack, etc.)
        print(f"ALERT: {message}")

# Use custom monitoring
connector = SAPODataConnector(config)
await connector.initialize()
connector.metrics = CustomMetricsCollector()
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Errors
```
Error: 401 Unauthorized
```
**Solution:**
```python
# Check credentials
config = ClientConfig(
    odata_service_url="https://your-system.com/service/",
    username="correct_username",
    password="correct_password"
)

# For OAuth2
config = ClientConfig(
    # ... other settings
    client_id="your_client_id",
    client_secret="your_client_secret"
)
```

#### 2. Rate Limiting Issues
```
Error: 429 Too Many Requests
```
**Solution:**
```python
config = ClientConfig(
    # ... other settings
    requests_per_second=1.0,  # Reduce rate
    max_workers=2            # Fewer concurrent workers
)
```

#### 3. Memory Issues with Large Datasets
```
Error: MemoryError
```
**Solution:**
```python
config = ClientConfig(
    # ... other settings
    batch_size=100,          # Smaller batches
    total_records_limit=10000, # Limit total records
    max_workers=2            # Reduce concurrency
)
```

#### 4. Network Timeout Issues
```python
# Increase timeouts in ODataConfig
class CustomODataConfig(ODataConfig):
    timeout: int = attrs.field(default=120)  # 2 minutes
    max_retries: int = attrs.field(default=5)
```

#### 5. Debugging Connection Issues
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show all HTTP requests and responses
```

### Performance Optimization Tips

1. **Batch Size Tuning:**
   - Start with 1000, adjust based on response times
   - Larger batches = fewer requests but more memory
   - Smaller batches = more requests but less memory

2. **Worker Count Optimization:**
   - Start with 3-5 workers
   - Monitor CPU and network utilization
   - SAP systems may have connection limits

3. **Rate Limiting:**
   - Start conservative (1-2 RPS)
   - Gradually increase while monitoring for errors
   - Different SAP systems have different limits

4. **Memory Management:**
   - Process entities in batches
   - Use streaming for very large datasets
   - Monitor memory usage during execution

### Monitoring and Logging

#### Enable Detailed Logging
```python
import structlog
import logging

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# The connector will automatically log:
# - Request/response details
# - Performance metrics
# - Error information
# - Progress updates
```

#### Custom Progress Tracking
```python
def detailed_progress_callback(progress):
    print(f"Entities: {progress['completed_entities']}/{progress['total_entities']}")
    print(f"Records: {progress['records_processed']}")
    print(f"Queue Size: {progress['queue_size']}")
    print(f"Success Rate: {progress['success_rate']:.2%}")
    
    # Log to file or monitoring system
    with open("progress.log", "a") as f:
        f.write(f"{datetime.now()}: {progress}\n")

connector.on_progress_update = detailed_progress_callback
```

This comprehensive guide covers the core concepts, architecture, and customization options for the SAP OData Connector. Use it as a reference for understanding the codebase and implementing custom solutions for your specific requirements.
