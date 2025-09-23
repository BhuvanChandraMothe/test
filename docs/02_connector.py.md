# connector.py - Main Orchestrator Documentation

## Overview
The `connector.py` file contains the `SAPODataConnector` class, which serves as the main orchestrator for the entire data extraction process. It coordinates all components and manages the complete lifecycle from initialization to cleanup.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import structlog
from datetime import datetime, timezone

from config.models import ClientConfig, ODataConfig, ConnectorSettings
from services.metadata import MetadataService
from services.count import CountService
from planning.graph_builder import RelationGraphBuilder
from planning.plan_generator import PlanGenerator, FetchCommand
from workers.proxy_pool import ProxyPool, ProxyResult
from storage.transformer import DataTransformer
from storage.local_storage import LocalFileStorage, LocalStorageConfig
from monitoring.metrics import MetricsCollector, PerformanceMonitor, AlertManager, setup_monitoring
from error_handling.dead_letter_queue import DeadLetterQueue, ErrorClassifier, FailureType
```

**Dependency Injection Pattern:**
- All major components are imported and will be instantiated as dependencies
- Each component has a single responsibility
- Loose coupling allows for easy testing and replacement

### Statistics Data Class
```python
@dataclass
class ConnectorStats:
    """Statistics for connector execution"""
    start_time: datetime
    end_time: Optional[datetime] = None
    entities_processed: int = 0
    records_processed: int = 0
    records_stored: int = 0
    commands_executed: int = 0
    commands_failed: int = 0
    
    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds"""
        if self.end_time is None:
            return (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Calculate command success rate"""
        total_commands = self.commands_executed + self.commands_failed
        if total_commands == 0:
            return 0.0
        return self.commands_executed / total_commands
    
    @property
    def records_per_second(self) -> float:
        """Calculate processing rate"""
        duration = self.duration_seconds
        if duration == 0:
            return 0.0
        return self.records_processed / duration
```

**Dataclass Concepts:**
- `@dataclass`: Automatically generates `__init__`, `__repr__`, etc.
- `@property`: Computed properties that act like attributes
- **Timezone-aware datetime**: Using `timezone.utc` for consistent timestamps
- **Defensive programming**: Handle division by zero cases

### Main Connector Class
```python
class SAPODataConnector:
    """Main SAP OData Connector orchestrator"""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.sap_config = self._create_sap_config()
        
        # Core components
        self.metadata_service: Optional[MetadataService] = None
        self.count_service: Optional[CountService] = None
        self.graph_builder = RelationGraphBuilder()
        self.plan_generator = PlanGenerator(
            batch_size=config.batch_size,
            max_concurrent_entities=config.max_workers
        )
        self.proxy_pool: Optional[ProxyPool] = None
        self.transformer: Optional[DataTransformer] = None
        
        # Storage components
        self.local_storage: Optional[LocalFileStorage] = None
        
        # Monitoring and error handling
        self.metrics: Optional[MetricsCollector] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None
        self.alert_manager: Optional[AlertManager] = None
        self.dead_letter_queue = DeadLetterQueue()
        
        # State
        self.is_running = False
        self.stats = ConnectorStats(start_time=datetime.now(timezone.utc))
        
        # Callbacks
        self.on_entity_completed: Optional[Callable[[str, int], None]] = None
        self.on_progress_update: Optional[Callable[[Dict[str, Any]], None]] = None
```

**Design Patterns Used:**

1. **Dependency Injection**: Components are injected rather than hard-coded
2. **Optional Typing**: `Optional[Type]` indicates components may be None initially
3. **Callback Pattern**: Allow external code to hook into events
4. **State Management**: Track connector state and statistics
5. **Builder Pattern**: Components are built up during initialization

### Configuration Transformation
```python
def _create_sap_config(self) -> ODataConfig:
    """Create ODataConfig from ClientConfig"""
    return ODataConfig(
        service_url=self.config.odata_service_url,
        username=self.config.username,
        password=self.config.password,
        client_id=self.config.client_id,
        client_secret=self.config.client_secret
    )
```

**Configuration Adapter Pattern:**
- Transforms user-friendly `ClientConfig` to internal `ODataConfig`
- Separates external API from internal implementation
- Allows for different configuration formats

### Async Initialization
```python
async def initialize(self):
    """Initialize all connector components"""
    logger.info("Initializing SAP OData Connector")
    
    try:
        # Setup monitoring
        self.metrics, self.performance_monitor, self.alert_manager = setup_monitoring()
        
        # Initialize services
        self.metadata_service = MetadataService(self.sap_config)
        self.count_service = CountService(self.sap_config)
        
        # Initialize proxy pool
        self.proxy_pool = ProxyPool(
            odata_config=self.sap_config,
            max_workers=self.config.max_workers
        )
        
        # Setup proxy pool callbacks
        self.proxy_pool.on_result = self._handle_proxy_result
        self.proxy_pool.on_error = self._handle_proxy_error
        
        # Initialize storage
        await self._initialize_storage()
        
        # Setup health checks
        self._setup_health_checks()
        
        logger.info("Connector initialization completed")
        
    except Exception as e:
        logger.error("Failed to initialize connector", error=str(e))
        raise
```

**Initialization Patterns:**
- **Async initialization**: Components that need async setup
- **Exception handling**: Catch and re-raise with context
- **Callback registration**: Wire up event handlers
- **Health check setup**: Prepare monitoring

### Storage Initialization
```python
async def _initialize_storage(self):
    """Initialize storage components"""
    # Local file storage
    storage_config = LocalStorageConfig(
        output_directory=self.config.output_directory,
        raw_data_directory=self.config.raw_data_directory,
        processed_data_directory=self.config.processed_data_directory
    )
    self.local_storage = LocalFileStorage(storage_config)
```

**Storage Abstraction:**
- Configuration object pattern for storage settings
- Separation of concerns between connector and storage
- Extensible for different storage backends

### Main Execution Flow
```python
async def run(self, selected_entities: Optional[List[str]] = None) -> ConnectorStats:
    """Run the complete data ingestion process"""
    logger.info("Starting SAP OData connector execution")
    
    try:
        self.is_running = True
        self.stats = ConnectorStats(start_time=datetime.now(timezone.utc))
        
        # Phase 1: Discovery and Planning
        await self._discovery_phase(selected_entities)
        
        # Phase 2: Execution
        await self._execution_phase()
        
        # Phase 3: Completion
        await self._completion_phase()
        
        self.stats.end_time = datetime.now(timezone.utc)
        
        logger.info("Connector execution completed successfully",
                   duration=self.stats.duration_seconds,
                   entities_processed=self.stats.entities_processed,
                   records_processed=self.stats.records_processed)
        
        return self.stats
        
    except Exception as e:
        logger.error("Connector execution failed", error=str(e))
        await self._handle_execution_error(e)
        raise
    
    finally:
        self.is_running = False
        await self._cleanup()
```

**Execution Flow Patterns:**
- **Three-phase execution**: Discovery → Execution → Completion
- **State management**: Track running state and statistics
- **Comprehensive error handling**: Catch, log, and cleanup
- **Finally block**: Ensure cleanup always happens

### Discovery Phase
```python
async def _discovery_phase(self, selected_entities: Optional[List[str]]):
    """Phase 1: Discover metadata and plan execution"""
    logger.info("Starting discovery phase")
    
    # Fetch metadata
    async with self.metadata_service:
        entity_schemas = await self.metadata_service.fetch_metadata()
    
    # Initialize transformer with schemas
    self.transformer = DataTransformer(entity_schemas)
    
    # Get entity counts
    entity_names = selected_entities or list(entity_schemas.keys())
    
    async with self.count_service:
        entity_counts = await self.count_service.get_entity_counts(entity_names)
    
    # Build dependency graph
    self.graph_builder.add_entities(entity_names)
    relationships = self.metadata_service.get_foreign_key_relationships()
    self.graph_builder.add_relationships(relationships)
    
    # Generate execution plan
    processing_order = self.graph_builder.get_processing_order()
    self.plan_generator.create_execution_plan(
        entity_counts, processing_order, selected_entities
    )
    
    logger.info("Discovery phase completed",
               entities=len(entity_names),
               total_records=sum(entity_counts.values()),
               processing_levels=len(processing_order))
```

**Discovery Phase Concepts:**
- **Context managers**: `async with` ensures proper resource cleanup
- **Metadata-driven processing**: Use schema information to guide execution
- **Dependency analysis**: Build graph of entity relationships
- **Plan generation**: Create optimized execution strategy

### Execution Phase
```python
async def _execution_phase(self):
    """Phase 2: Execute data fetching and processing"""
    logger.info("Starting execution phase")
    
    # Start proxy pool
    await self.proxy_pool.start()
    
    # Get initial commands
    initial_commands = self.plan_generator.get_initial_commands()
    await self.proxy_pool.add_commands(initial_commands)
    
    # Monitor execution
    await self._monitor_execution()
    
    logger.info("Execution phase completed")
```

**Execution Patterns:**
- **Worker pool startup**: Initialize concurrent processing
- **Command queuing**: Add work items to processing queue
- **Execution monitoring**: Track progress and handle results

### Execution Monitoring
```python
async def _monitor_execution(self):
    """Monitor execution progress and handle results"""
    while self.proxy_pool.is_running or not self.proxy_pool.is_queue_empty():
        # Check for completed results
        results = await self.proxy_pool.get_results(timeout=1.0)
        
        for result in results:
            await self._process_result(result)
        
        # Update progress
        await self._update_progress()
        
        # Check for new commands
        new_commands = self.plan_generator.get_next_commands()
        if new_commands:
            await self.proxy_pool.add_commands(new_commands)
        
        # Small delay to prevent busy waiting
        await asyncio.sleep(0.1)
```

**Monitoring Loop Patterns:**
- **Event loop**: Continuously check for work and results
- **Non-blocking operations**: Use timeouts to avoid blocking
- **Progress updates**: Regular status reporting
- **Dynamic command generation**: Add new work as dependencies are satisfied

### Result Processing
```python
async def _process_result(self, result: ProxyResult):
    """Process a single result from the proxy pool"""
    if result.success:
        # Store raw data
        await self._store_raw_data(result)
        
        # Transform and store processed data
        await self._transform_and_store(result)
        
        # Update statistics
        self.stats.commands_executed += 1
        self.stats.records_processed += len(result.data.get('value', []))
        
        # Check for pagination
        if result.next_link:
            next_command = self._create_next_page_command(result)
            await self.proxy_pool.add_commands([next_command])
        
        # Notify completion
        if self.on_entity_completed:
            self.on_entity_completed(result.command.entity_set, len(result.data.get('value', [])))
    
    else:
        # Handle failure
        await self._handle_failed_result(result)
        self.stats.commands_failed += 1
```

**Result Processing Concepts:**
- **Success/failure branching**: Handle both success and error cases
- **Data pipeline**: Raw storage → Transformation → Processed storage
- **Pagination handling**: Automatically generate next page commands
- **Statistics tracking**: Update counters for monitoring
- **Event notification**: Callback pattern for external monitoring

### Data Storage
```python
async def _store_raw_data(self, result: ProxyResult):
    """Store raw response data"""
    batch_info = {
        'page_number': result.command.skip // result.command.top + 1,
        'batch_size': result.command.top,
        'entity_set': result.command.entity_set,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    file_path = await self.local_storage.store_raw_response(
        entity_name=result.command.entity_set,
        response_data=result.data,
        batch_info=batch_info
    )
    
    logger.debug("Stored raw data", file_path=file_path, entity=result.command.entity_set)
```

**Storage Patterns:**
- **Metadata enrichment**: Add batch information to stored data
- **Structured file naming**: Consistent naming for easy retrieval
- **Async I/O**: Non-blocking file operations
- **Audit trail**: Include timestamps and processing information

### Data Transformation
```python
async def _transform_and_store(self, result: ProxyResult):
    """Transform raw data and store processed records"""
    if not result.data or 'value' not in result.data:
        return
    
    records = result.data['value']
    transformed_records = []
    
    for record in records:
        try:
            transformed_record = await self.transformer.transform_record(
                entity_name=result.command.entity_set,
                raw_record=record
            )
            transformed_records.append(transformed_record)
            
        except Exception as e:
            logger.error("Failed to transform record",
                        entity=result.command.entity_set,
                        error=str(e))
            # Continue processing other records
    
    # Store transformed records
    if transformed_records:
        await self.local_storage.store_transformed_records(
            entity_name=result.command.entity_set,
            records=transformed_records
        )
        
        self.stats.records_stored += len(transformed_records)
```

**Transformation Patterns:**
- **Error isolation**: Continue processing if individual records fail
- **Batch processing**: Transform multiple records together
- **Error logging**: Detailed error information for debugging
- **Statistics tracking**: Count successfully processed records

### Error Handling
```python
async def _handle_failed_result(self, result: ProxyResult):
    """Handle failed command results"""
    command = result.command
    error = result.error
    
    # Classify error type
    error_type = ErrorClassifier.classify_error(error)
    
    # Determine if retry is possible
    if command.can_retry() and error_type in [FailureType.NETWORK, FailureType.TIMEOUT]:
        # Create retry command
        retry_command = command.create_retry_command()
        await self.proxy_pool.add_commands([retry_command])
        
        logger.warning("Retrying failed command",
                      command_id=command.command_id,
                      retry_count=retry_command.retry_count,
                      error=error)
    else:
        # Send to dead letter queue
        await self.dead_letter_queue.add_failed_command(command, error, error_type)
        
        logger.error("Command failed permanently",
                    command_id=command.command_id,
                    entity=command.entity_set,
                    error=error,
                    error_type=error_type.value)
```

**Error Handling Strategies:**
- **Error classification**: Categorize errors for appropriate handling
- **Retry logic**: Automatic retry for transient failures
- **Dead letter queue**: Permanent storage for failed commands
- **Detailed logging**: Comprehensive error information

### Progress Updates
```python
async def _update_progress(self):
    """Update progress and notify callbacks"""
    if not self.on_progress_update:
        return
    
    progress = {
        'completed_entities': self.stats.entities_processed,
        'total_entities': len(self.plan_generator.entity_plans),
        'records_processed': self.stats.records_processed,
        'records_stored': self.stats.records_stored,
        'commands_executed': self.stats.commands_executed,
        'commands_failed': self.stats.commands_failed,
        'queue_size': self.proxy_pool.queue_size,
        'success_rate': self.stats.success_rate,
        'duration_seconds': self.stats.duration_seconds,
        'records_per_second': self.stats.records_per_second
    }
    
    try:
        self.on_progress_update(progress)
    except Exception as e:
        logger.error("Progress callback failed", error=str(e))
        # Don't let callback errors stop execution
```

**Progress Reporting Patterns:**
- **Comprehensive metrics**: Include all relevant statistics
- **Callback isolation**: Don't let callback errors affect main execution
- **Performance metrics**: Calculate rates and percentages
- **Non-blocking**: Progress updates don't slow down processing

### Cleanup and Resource Management
```python
async def _cleanup(self):
    """Cleanup resources and connections"""
    logger.info("Cleaning up connector resources")
    
    try:
        # Stop proxy pool
        if self.proxy_pool:
            await self.proxy_pool.stop()
        
        # Close storage connections
        if self.local_storage:
            await self.local_storage.close()
        
        # Stop monitoring
        if self.performance_monitor:
            await self.performance_monitor.stop()
        
        # Final metrics
        if self.metrics:
            await self.metrics.flush()
            
    except Exception as e:
        logger.error("Error during cleanup", error=str(e))
        # Don't raise exceptions during cleanup
```

**Resource Management:**
- **Graceful shutdown**: Stop all components properly
- **Exception isolation**: Don't let cleanup errors propagate
- **Resource ordering**: Close resources in appropriate order
- **Final operations**: Flush metrics and logs

## Key Programming Concepts

### 1. **Orchestration Pattern**
- Central coordinator manages multiple components
- Each component has single responsibility
- Loose coupling through dependency injection

### 2. **Async/Await Architecture**
- Non-blocking I/O throughout the system
- Concurrent processing with proper coordination
- Resource management with async context managers

### 3. **Event-Driven Design**
- Callback pattern for progress reporting
- Result processing through event handling
- Monitoring through continuous event loops

### 4. **Error Handling Strategy**
- Multiple levels of error handling
- Retry logic with exponential backoff
- Dead letter queue for permanent failures

### 5. **State Management**
- Centralized statistics tracking
- Component lifecycle management
- Progress monitoring and reporting

### 6. **Pipeline Architecture**
- Discovery → Planning → Execution → Storage
- Data transformation pipeline
- Result processing pipeline

This file demonstrates enterprise-grade orchestration patterns, async programming, and comprehensive error handling for large-scale data processing systems.
