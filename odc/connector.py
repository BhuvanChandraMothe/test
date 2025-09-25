import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import structlog
from datetime import datetime, timezone

# Setup logging before any other imports
from .utils.logging_config import setup_connector_logging
setup_connector_logging()

from .config.models import ClientConfig, ODataConfig, ConnectorSettings
from .services.metadata import MetadataService
from .services.count import CountService
from .planning.graph_builder import RelationGraphBuilder
from .planning.plan_generator import PlanGenerator
from .workers.proxy_pool import ProxyPool, ProxyResult
from .storage.transformer import DataTransformer
from .storage.local_storage import LocalFileStorage, LocalStorageConfig
from .monitoring.metrics import MetricsCollector, PerformanceMonitor, AlertManager, setup_monitoring, get_metrics_collector
from .error_handling.dead_letter_queue import DeadLetterQueue, ErrorClassifier, FailureType

from prometheus_client import CollectorRegistry, push_to_gateway

logger = structlog.get_logger(__name__)



PUSH_GATEWAY_URL = 'http://localhost:9091' 
PROMETHEUS_JOB_NAME = 'northwind_connector'


@dataclass
class ConnectorStats:
    """Statistics for the connector execution"""
    start_time: datetime
    end_time: Optional[datetime] = None
    entities_processed: int = 0
    records_processed: int = 0
    records_stored: int = 0
    commands_executed: int = 0
    commands_failed: int = 0
    
    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()


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
            max_concurrent_entities=config.max_workers,
            total_records_limit=config.total_records_limit
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
    
    def _create_sap_config(self) -> ODataConfig:
        """Create ODataConfig from ClientConfig"""
        return ODataConfig(
            service_url=self.config.odata_service_url,
            username=self.config.username,
            password=self.config.password,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            max_connections=self.config.max_connections
        )
    
    async def initialize(self):
        """Initialize all connector components with connection testing"""
        logger.info("Initializing SAP OData Connector")
        
        try:
            # Setup monitoring
            self.metrics, self.performance_monitor, self.alert_manager = setup_monitoring()
            
            # Initialize services
            self.metadata_service = MetadataService(self.sap_config)
            self.count_service = CountService(self.sap_config)
            
            # STEP 1: Test connection and validate credentials
            logger.info("Step 1: Testing connection to OData service")
            await self._test_connection()
            
            # STEP 2: Fetch metadata and save Entity Relationship file
            logger.info("Step 2: Fetching metadata and creating Entity Relationship file")
            await self._fetch_and_save_metadata()
            
            # STEP 3: Show API endpoints that will be accessed
            logger.info("Step 3: Analyzing API endpoints that will be accessed")
            await self._show_api_endpoints()
            
            # Initialize proxy pool
            self.proxy_pool = ProxyPool(
                odata_config=self.sap_config,
                max_workers=self.config.max_workers
            )
            
            # STEP 4: Validate connection pool
            logger.info("Step 4: Validating connection pool")
            await self._validate_connection_pool()
            
            # Setup proxy pool callbacks
            self.proxy_pool.on_result = self._handle_proxy_result
            self.proxy_pool.on_error = self._handle_proxy_error
            
            # Initialize storage
            await self._initialize_storage()
            
            # Add health checks
            self._setup_health_checks()
            
            logger.info("Connector initialization completed successfully")
            
        except Exception as e:
            logger.error("Failed to initialize connector", error=str(e))
            raise
    
    async def _test_connection(self):
        """Test connection to OData service"""
        logger.info("Testing connection to OData service...")
        
        async with self.metadata_service:
            connection_ok = await self.metadata_service.test_connection()
            
            if not connection_ok:
                raise ConnectionError(
                    "Failed to establish connection to OData service. "
                    "Please check your service URL and credentials."
                )
            
            logger.info("Connection test successful")
    
    async def _fetch_and_save_metadata(self):
        """Fetch metadata and save Entity Relationship file"""
        logger.info("Fetching metadata from OData service...")
        
        async with self.metadata_service:
            # Fetch metadata
            entity_schemas = await self.metadata_service.fetch_metadata()
            
            # Save Entity Relationship file
            er_file_path = await self.metadata_service.save_entity_relationship_file(
                self.config.output_directory
            )
            
            logger.info("Metadata fetched and Entity Relationship file saved", 
                       entities_count=len(entity_schemas),
                       er_file=er_file_path)
    
    async def _show_api_endpoints(self):
        """Show all API endpoints that will be accessed during execution"""
        logger.info("Analyzing API endpoints for upcoming execution...")
        
        # Get entity schemas from metadata service
        entity_schemas = self.metadata_service.schemas
        
        # Determine which entities to process (same logic as in discovery phase)
        if self.config.selected_modules:
            entity_names = self.config.selected_modules
        else:
            entity_names = list(entity_schemas.keys())
        
        # Get entity counts
        async with self.count_service:
            entity_counts = await self.count_service.get_entity_counts(entity_names)
        
        # SHOW ALL API ENDPOINTS THAT WILL BE HIT
        logger.info("=" * 80)
        logger.info("🌐 API ENDPOINTS THAT WILL BE ACCESSED:")
        logger.info("=" * 80)
        
        # Show metadata and count endpoints first
        logger.info("📋 Initial Discovery Endpoints:")
        logger.info(f"   1. Metadata: {self.sap_config.service_url}/$metadata")
        logger.info(f"   2. Service Document: {self.sap_config.service_url}/")
        
        # Show count endpoints
        logger.info(f"\n🔢 Entity Count Endpoints ({len(entity_names)} entities):")
        for i, entity_name in enumerate(entity_names, 1):
            count_url = f"{self.sap_config.service_url}/{entity_name}/$count"
            logger.info(f"   {i:2d}. {entity_name}: {count_url}")
        
        # Show data fetch endpoints with pagination info
        logger.info(f"\n📊 Data Fetch Endpoints (with pagination):")
        total_expected_records = 0
        total_requests = 0
        
        for i, entity_name in enumerate(entity_names, 1):
            base_url = f"{self.sap_config.service_url}/{entity_name}"
            record_count = entity_counts.get(entity_name, 0)
            total_expected_records += record_count
            
            # Calculate number of requests needed
            batch_size = self.config.batch_size
            requests_needed = max(1, (record_count + batch_size - 1) // batch_size) if record_count > 0 else 1
            total_requests += requests_needed
            
            logger.info(f"   {i:2d}. {entity_name}:")
            logger.info(f"       Base URL: {base_url}")
            logger.info(f"       Records: {record_count:,}")
            logger.info(f"       Requests: {requests_needed} (batch size: {batch_size})")
            
            # Show first few pagination URLs as examples
            if record_count > 0:
                logger.info(f"       Examples:")
                logger.info(f"         - {base_url}?$skip=0&$top={min(batch_size, record_count)}")
                if requests_needed > 1:
                    logger.info(f"         - {base_url}?$skip={batch_size}&$top={batch_size}")
                if requests_needed > 2:
                    logger.info(f"         - ... ({requests_needed - 2} more requests)")
        
        # Apply record limit if configured
        actual_records_to_process = total_expected_records
        if self.config.total_records_limit:
            actual_records_to_process = min(total_expected_records, self.config.total_records_limit)
        
        logger.info(f"\n📈 EXECUTION SUMMARY:")
        logger.info(f"   Total Entities: {len(entity_names)}")
        logger.info(f"   Total Available Records: {total_expected_records:,}")
        if self.config.total_records_limit:
            logger.info(f"   Record Limit Applied: {self.config.total_records_limit:,}")
            logger.info(f"   Actual Records to Process: {actual_records_to_process:,}")
        else:
            logger.info(f"   Records to Process: {actual_records_to_process:,}")
        logger.info(f"   Estimated HTTP Requests: {total_requests + len(entity_names) + 2:,}")
        logger.info(f"   Batch Size: {self.config.batch_size}")
        logger.info(f"   Max Workers: {self.config.max_workers}")
        logger.info(f"   Max Connections: {self.config.max_connections}")
        logger.info(f"   Rate Limit: {self.config.requests_per_second} req/sec")
        
        logger.info("=" * 80)
    
    async def _validate_connection_pool(self):
        """Validate connection pool"""
        if self.proxy_pool and self.proxy_pool.resilience:
            pool_valid = await self.proxy_pool.resilience.connection_pool.validate_connection()
            
            if not pool_valid:
                raise ConnectionError(
                    "Connection pool validation failed. "
                    "Unable to establish reliable connections to OData service."
                )
            
            logger.info("Connection pool validation successful")
    
    async def _initialize_storage(self):
        """Initialize storage components"""
        # Local file storage
        storage_config = LocalStorageConfig(
            output_directory=self.config.output_directory,
            raw_data_directory=self.config.raw_data_directory,
            processed_data_directory=self.config.processed_data_directory
        )
        self.local_storage = LocalFileStorage(storage_config)
    
    def _setup_health_checks(self):
        """Setup health check functions"""
        if self.performance_monitor:
            self.performance_monitor.add_health_check(
                "proxy_pool", lambda: self.proxy_pool.is_running if self.proxy_pool else False
            )
            self.performance_monitor.add_health_check(
                "dead_letter_queue", lambda: not self.dead_letter_queue.is_full()
            )
    
    async def run(self, selected_entities: Optional[List[str]] = None) -> ConnectorStats:
        """Run the complete data ingestion process"""
        logger.info("Starting SAP OData connector execution")
        
        try:
            self.is_running = True
            self.stats = ConnectorStats(start_time=datetime.now(timezone.utc))
            
            # Reset the global record tracker for clean state
            from .planning.record_tracker import reset_global_tracker
            reset_global_tracker()
            # Update plan generator to use the new tracker
            from .planning.record_tracker import get_global_tracker
            self.plan_generator.record_tracker = get_global_tracker()
            if self.config.total_records_limit:
                self.plan_generator.record_tracker.set_total_records_limit(self.config.total_records_limit)
            
            # Phase 1: Discovery and Planning
            await self._discovery_phase(selected_entities)
            
            # Phase 2: Execution
            await self._execution_phase()
            
            # Phase 3: Completion
            await self._completion_phase()
            
            self.stats.end_time = datetime.now(timezone.utc)
            
            # Skip the problematic global status check that causes hanging
            logger.info("Final execution summary:")
            logger.info(f"   - Duration: {self.stats.duration_seconds:.2f} seconds")
            logger.info(f"   - Records processed: {self.stats.records_processed}")
            logger.info(f"   - Commands executed: {self.stats.commands_executed}")
            logger.info(f"   - Commands failed: {self.stats.commands_failed}")
            
            # Try to get global status but don't hang if it fails
            try:
                if hasattr(self.plan_generator, 'record_tracker'):
                    global_status = await asyncio.wait_for(
                        self.plan_generator.record_tracker.get_global_status(), 
                        timeout=2.0
                    )
                    logger.info(f"   - Global records fetched: {global_status.get('global_records_fetched', 0)}")
                    logger.info(f"   - Entities tracked: {global_status.get('entities_tracked', 0)}")
                    logger.info(f"   - Entities complete: {global_status.get('entities_complete', 0)}")
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception) as e:
                logger.warning(f"Could not get final global status: {e}")
            
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
    
    async def _discovery_phase(self, selected_entities: Optional[List[str]]):
        """Phase 1: Discover metadata and plan execution"""
        logger.info("Starting discovery phase")
        
        # Fetch metadata
        async with self.metadata_service:
            entity_schemas = await self.metadata_service.fetch_metadata()
        
        # Initialize transformer with schemas
        self.transformer = DataTransformer(entity_schemas)
        
        # Get entity counts
        # Determine which entities to process:
        # 1. Use selected_entities parameter if provided
        # 2. Otherwise use config.selected_modules if not empty
        # 3. Otherwise process all entities
        if selected_entities is not None:
            entity_names = selected_entities
        elif self.config.selected_modules:
            entity_names = self.config.selected_modules
        else:
            entity_names = list(entity_schemas.keys())
            
        logger.info("Entity selection determined", 
                   selected_entities_param=selected_entities,
                   config_selected_modules=self.config.selected_modules,
                   final_entity_count=len(entity_names),
                   entities=entity_names[:5] if len(entity_names) > 5 else entity_names)
        
        # Get entity counts (no display, just for planning)
        async with self.count_service:
            entity_counts = await self.count_service.get_entity_counts(entity_names)
        
        # Build dependency graph
        self.graph_builder.add_entities(entity_names)
        relationships = self.metadata_service.get_foreign_key_relationships()
        self.graph_builder.add_relationships(relationships)
        
        # Generate execution plan
        processing_order = self.graph_builder.get_processing_order()
        await self.plan_generator.create_execution_plan(
            entity_counts, processing_order, entity_names
        )
        
        logger.info("Discovery phase completed",
                   entities=len(entity_names),
                   total_records=sum(entity_counts.values()),
                   processing_levels=len(processing_order))
        
        # Log the execution plan summary
        logger.info("Execution plan summary:")
        for level_idx, level_entities in enumerate(processing_order):
            level_total = sum(entity_counts.get(entity, 0) for entity in level_entities)
            logger.info(f"   Level {level_idx + 1}: {len(level_entities)} entities, {level_total} records")
            for entity in level_entities:
                if entity in entity_counts:
                    logger.info(f"     - {entity}: {entity_counts[entity]} records")
    
    async def _execution_phase(self):
        """Phase 2: Execute data fetching and processing"""
        logger.info("Starting execution phase")
        
        # Start proxy pool
        await self.proxy_pool.start()
        
        # Get all commands from the plan generator and add them to the queue
        all_commands = self.plan_generator.get_all_commands()
        await self.proxy_pool.add_commands(all_commands)
        
        # Monitor execution by waiting for all tasks to complete
        await self._monitor_execution()
        
        logger.info("Execution phase completed")
        
    async def _monitor_execution(self):
        """Monitor the execution progress by waiting for the proxy pool to complete."""
        logger.info("Starting execution monitoring")
        if self.proxy_pool:
            # Use a much more aggressive timeout-based approach
            max_wait_time = 60   # 1 minute maximum wait
            check_interval = 1   # Check every 1 second
            elapsed_time = 0
            consecutive_empty_checks = 0
            
            while elapsed_time < max_wait_time:
                queue_size = self.proxy_pool.get_queue_size()
                pool_stats = self.proxy_pool.get_pool_stats()
                active_workers = pool_stats.get('active_workers', 0)
                
                logger.info(f"Monitoring: Queue size: {queue_size}, Active workers: {active_workers}, Time: {elapsed_time}s")
                
                # If queue is empty and no workers are active, we're done
                if queue_size == 0 and active_workers == 0:
                    consecutive_empty_checks += 1
                    logger.info(f"Empty check #{consecutive_empty_checks} - queue empty and no active workers")
                    
                    # If we've seen empty state for 3 consecutive checks, we're definitely done
                    if consecutive_empty_checks >= 3:
                        logger.info("All tasks completed - confirmed empty state")
                        break
                else:
                    consecutive_empty_checks = 0
                
                # Additional check: if we've been waiting too long, just exit
                if elapsed_time >= 30:  # After 30 seconds, be more aggressive
                    logger.warning(f"Long wait detected ({elapsed_time}s) - forcing completion")
                    break
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
            
            if elapsed_time >= max_wait_time:
                logger.warning("Monitoring timeout reached - forcing completion")
            
            # Force stop the proxy pool to ensure clean exit
            logger.info("Forcing proxy pool stop to ensure clean exit")
            if self.proxy_pool.is_running:
                await self.proxy_pool.stop()
        
        logger.info("Execution monitoring complete - all tasks finished.")
        
    async def _completion_phase(self):
        """Phase 3: Complete execution and cleanup"""
        logger.info("Starting completion phase")
        
        for entity_name in self.plan_generator.entity_plans.keys():
            await self.local_storage.save_unified_processed_records(entity_name)
        
        if self.proxy_pool:
            await self.proxy_pool.stop()
        
    async def _process_successful_result(self, result: ProxyResult):
        """Process successful result - transform and store"""
        try:
            transformed_records = await self.transformer.transform_odata_response(
                result.command.entity_set,
                result.data
            )
            
            if transformed_records:
                is_first_batch = (result.command.skip == 0)
                records_fetched = await self.plan_generator.record_tracker.get_entity_records_fetched(result.command.entity_set)
                is_last_batch = (result.command.skip + result.command.top >= records_fetched)
                await self.local_storage.store_processed_records(
                    result.command.entity_set,
                    transformed_records,
                    is_first_batch=is_first_batch,
                    is_last_batch=is_last_batch
                )

                # Store raw data for debugging purposes
                await self.local_storage.store_raw_response(
                    result.command.entity_set,
                    result.command.command_id,
                    result.data
                )
            
            self.stats.records_processed += len(transformed_records)
            self.stats.records_stored += len(transformed_records)
            
        except Exception as e:
            logger.error("Failed to process successful result", error=str(e))
            # Add to DLQ as transformation/storage error
            await self.dead_letter_queue.add_failed_command(
                result.command,
                FailureType.TRANSFORMATION_ERROR,
                str(e)
            )
    
    async def _handle_proxy_error(self, result: ProxyResult):
        """Handle proxy error result"""
        try:
            self.stats.commands_failed += 1
            
            # Classify error
            failure_type = ErrorClassifier.classify_exception(
                Exception(result.error)
            )
            
            # Check if retryable
            if ErrorClassifier.is_retryable(failure_type) and result.command.can_retry():
                # Create retry command
                retry_command = result.command.create_retry_command()
                await self.proxy_pool.add_command(retry_command)
                logger.info("Command scheduled for retry", 
                           command_id=retry_command.command_id,
                           retry_count=retry_command.retry_count)
            else:
                # Add to dead letter queue
                await self.dead_letter_queue.add_failed_command(
                    result.command,
                    failure_type,
                    result.error or "Unknown error"
                )
            
            # Record metrics
            if self.metrics:
                self.metrics.record_request(
                    entity=result.command.entity_set,
                    worker_id="unknown",
                    duration=0.0,
                    success=False,
                    error_type=failure_type.value
                )
            
        except Exception as e:
            logger.error("Error handling proxy error", error=str(e))
    
    async def _handle_proxy_result(self, result: ProxyResult):
        """Handle successful proxy result"""
        try:
            if result.success and result.data:
                # Transform and store data
                await self._process_successful_result(result)
            
            self.stats.commands_executed += 1
            
            # Record metrics
            if self.metrics:
                self.metrics.record_request(
                    entity=result.command.entity_set,
                    worker_id="unknown",
                    duration=result.duration if hasattr(result, 'duration') else 0.0,
                    success=result.success
                )
            
        except Exception as e:
            logger.error("Error handling proxy result", error=str(e))
    
    async def _handle_execution_error(self, error: Exception):
        """Handle execution-level errors"""
        if self.alert_manager:
            await self.alert_manager.trigger_alert(
                severity="critical",
                title="Connector Execution Failed",
                message=str(error),
                metadata={'error_type': type(error).__name__}
            )
            
    async def _push_metrics_to_gateway(self):
        """Push metrics to the Prometheus Push Gateway."""
        if self.metrics and self.metrics.registry:
            try:
                PUSH_GATEWAY_URL = 'http://localhost:9091'
                PROMETHEUS_JOB_NAME = 'sap_odata_connector'
                
                push_to_gateway(
                    PUSH_GATEWAY_URL,
                    job=PROMETHEUS_JOB_NAME,
                    registry=self.metrics.registry
                )
                logger.info("Metrics pushed to Prometheus Push Gateway successfully.")
            except Exception as e:
                logger.error("Failed to push metrics to Push Gateway", error=str(e))
        else:
            logger.warning("Metrics collector or registry is not available. Skipping push.")
    
    async def _cleanup(self):
        """Cleanup resources - simplified to avoid hanging"""
        logger.info("Cleaning up connector resources")
        
        try:
            if self.proxy_pool:
                if self.proxy_pool.is_running:
                    logger.info("Stopping proxy pool during cleanup")
                    # Use timeout to avoid hanging
                    await asyncio.wait_for(self.proxy_pool.stop(), timeout=5.0)
                else:
                    logger.info("Proxy pool already stopped")
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception) as e:
            logger.warning(f"Cleanup timeout or error (this is OK): {e}")
        
        logger.info("Connector cleanup completed")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        dlq_stats = self.dead_letter_queue.get_statistics()
        
        summary = {
            'execution_stats': {
                'start_time': self.stats.start_time.isoformat(),
                'end_time': self.stats.end_time.isoformat() if self.stats.end_time else None,
                'duration_seconds': self.stats.duration_seconds,
                'entities_processed': self.stats.entities_processed,
                'records_processed': self.stats.records_processed,
                'records_stored': self.stats.records_stored,
                'commands_executed': self.stats.commands_executed,
                'commands_failed': self.stats.commands_failed
            },
            'dead_letter_queue': dlq_stats,
            'plan_summary': self.plan_generator.get_plan_summary() if self.plan_generator else {},
            'graph_stats': self.graph_builder.get_graph_stats() if self.graph_builder else {}
        }
        
        if self.transformer:
            summary['transformation_stats'] = self.transformer.get_transformation_stats()
        
        return summary
    
    async def export_failed_commands(self, file_path: str):
        """Export failed commands for analysis"""
        await self.dead_letter_queue.export_failed_commands(file_path)
    
    async def retry_failed_commands(self, command_ids: List[str]) -> int:
        """Retry specific failed commands"""
        retried_count = 0
        
        for command_id in command_ids:
            command = await self.dead_letter_queue.retry_failed_command(command_id)
            if command and self.proxy_pool:
                await self.proxy_pool.add_command(command)
                retried_count += 1
        
        return retried_count


# Factory function for easy connector creation
def create_connector(config_file: Optional[str] = None) -> SAPODataConnector:
    """Create SAP OData Connector from configuration"""
    settings = ConnectorSettings(config_file)
    client_config = settings.get_client_config()
    return SAPODataConnector(client_config)