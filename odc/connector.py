"""Main SAP OData Connector orchestrator"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import structlog
from datetime import datetime, timezone

# Setup logging before any other imports
from utils.logging_config import setup_connector_logging
setup_connector_logging()

from config.models import ClientConfig, ODataConfig, ConnectorSettings
from services.metadata import MetadataService
from services.count import CountService
from planning.graph_builder import RelationGraphBuilder
from planning.plan_generator import PlanGenerator
from workers.proxy_pool import ProxyPool, ProxyResult
from storage.transformer import DataTransformer
from storage.local_storage import LocalFileStorage, LocalStorageConfig
from monitoring.metrics import MetricsCollector, PerformanceMonitor, AlertManager, setup_monitoring, get_metrics_collector
from error_handling.dead_letter_queue import DeadLetterQueue, ErrorClassifier, FailureType

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
            client_secret=self.config.client_secret
        )
    
    async def initialize(self):
        """Initialize all connector components with connection testing"""
        logger.info("🚀 Initializing SAP OData Connector")
        
        try:
            # Setup monitoring
            self.metrics, self.performance_monitor, self.alert_manager = setup_monitoring()
            
            # Initialize services
            self.metadata_service = MetadataService(self.sap_config)
            self.count_service = CountService(self.sap_config)
            
            # STEP 1: Test connection and validate credentials
            logger.info("🔍 Step 1: Testing connection to OData service")
            await self._test_connection()
            
            # STEP 2: Fetch metadata and save Entity Relationship file
            logger.info("📋 Step 2: Fetching metadata and creating Entity Relationship file")
            await self._fetch_and_save_metadata()
            
            # Initialize proxy pool
            self.proxy_pool = ProxyPool(
                odata_config=self.sap_config,
                max_workers=self.config.max_workers
            )
            
            # STEP 3: Validate connection pool
            logger.info("🔗 Step 3: Validating connection pool")
            await self._validate_connection_pool()
            
            # Setup proxy pool callbacks
            self.proxy_pool.on_result = self._handle_proxy_result
            self.proxy_pool.on_error = self._handle_proxy_error
            
            # Initialize storage
            await self._initialize_storage()
            
            # Add health checks
            self._setup_health_checks()
            
            logger.info("✅ Connector initialization completed successfully")
            
        except Exception as e:
            logger.error("❌ Failed to initialize connector", error=str(e))
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
            
            logger.info("✅ Connection test successful")
    
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
            
            logger.info("✅ Metadata fetched and Entity Relationship file saved", 
                       entities_count=len(entity_schemas),
                       er_file=er_file_path)
    
    async def _validate_connection_pool(self):
        """Validate connection pool"""
        if self.proxy_pool and self.proxy_pool.resilience:
            pool_valid = await self.proxy_pool.resilience.connection_pool.validate_connection()
            
            if not pool_valid:
                raise ConnectionError(
                    "Connection pool validation failed. "
                    "Unable to establish reliable connections to OData service."
                )
            
            logger.info("✅ Connection pool validation successful")
    
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
            from planning.record_tracker import reset_global_tracker
            reset_global_tracker()
            # Update plan generator to use the new tracker
            from planning.record_tracker import get_global_tracker
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
            
            # Get final record tracker status for comparison
            if hasattr(self.plan_generator, 'record_tracker'):
                global_status = await self.plan_generator.record_tracker.get_global_status()
                logger.info("📊 Final execution summary:")
                logger.info(f"  ✅ Duration: {self.stats.duration_seconds:.2f} seconds")
                logger.info(f"  📈 Records processed: {self.stats.records_processed}")
                logger.info(f"  📋 Commands executed: {self.stats.commands_executed}")
                logger.info(f"  ❌ Commands failed: {self.stats.commands_failed}")
                logger.info(f"  🎯 Global records fetched: {global_status.get('global_records_fetched', 0)}")
                logger.info(f"  📊 Entities tracked: {global_status.get('entities_tracked', 0)}")
                logger.info(f"  ✅ Entities complete: {global_status.get('entities_complete', 0)}")
            
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
        
        async with self.count_service:
            entity_counts = await self.count_service.get_entity_counts(entity_names)
        
        # Log endpoint information for each entity FIRST
        logger.info("📋 Endpoints to be processed:")
        total_expected_records = 0
        for entity_name in entity_names:
            endpoint_url = f"{self.sap_config.service_url}/{entity_name}"
            record_count = entity_counts.get(entity_name, 0)
            total_expected_records += record_count
            logger.info(f"  🔗 {entity_name}: {endpoint_url} (Expected records: {record_count})")
        
        logger.info(f"📊 Total expected records across all entities: {total_expected_records}")
        
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
        logger.info("📋 Execution plan summary:")
        for level_idx, level_entities in enumerate(processing_order):
            level_total = sum(entity_counts.get(entity, 0) for entity in level_entities)
            logger.info(f"  Level {level_idx + 1}: {len(level_entities)} entities, {level_total} records")
            for entity in level_entities:
                if entity in entity_counts:
                    logger.info(f"    - {entity}: {entity_counts[entity]} records")
    
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
    
    async def _monitor_execution(self):
        """Monitor the execution progress"""
        completed_entities = set()
        last_progress_log = 0
        
        logger.info("🔍 Starting execution monitoring")
        
        while self.is_running:
            # Update metrics
            if self.metrics and self.proxy_pool:
                pool_stats = self.proxy_pool.get_pool_stats()
                self.metrics.update_queue_size(pool_stats['queue_size'])
                self.metrics.update_active_workers(pool_stats['active_workers'])
            
            # Check if execution is complete
            # We need both: empty queue AND no active workers
            pool_stats = self.proxy_pool.get_pool_stats()
            queue_empty = pool_stats['queue_size'] == 0
            no_active_workers = pool_stats['active_workers'] == 0
            
            if queue_empty and no_active_workers:
                logger.info("✅ Execution monitoring complete - all work finished", 
                           queue_size=pool_stats['queue_size'],
                           active_workers=pool_stats['active_workers'],
                           records_processed=self.stats.records_processed,
                           commands_executed=self.stats.commands_executed)
                break  # Exit immediately when queue is empty and no workers are active
            
            # Progress update callback
            if self.on_progress_update:
                progress_info = {
                    'queue_size': pool_stats['queue_size'],
                    'active_workers': pool_stats['active_workers'],
                    'completed_entities': len(completed_entities),
                    'records_processed': self.stats.records_processed,
                    'commands_executed': self.stats.commands_executed,
                    'commands_failed': self.stats.commands_failed
                }
                self.on_progress_update(progress_info)
            
            # Log progress periodically (every 10 seconds when active)
            current_time = asyncio.get_event_loop().time()
            if (pool_stats['queue_size'] > 0 or pool_stats['active_workers'] > 0) and \
               (current_time - last_progress_log) >= 10:
                logger.info("📊 Execution progress", 
                           queue_size=pool_stats['queue_size'],
                           active_workers=pool_stats['active_workers'],
                           records_processed=self.stats.records_processed,
                           commands_executed=self.stats.commands_executed)
                last_progress_log = current_time
            
            await asyncio.sleep(1)
    
    async def _completion_phase(self):
        """Phase 3: Complete execution and cleanup"""
        logger.info("Starting completion phase")
        
        # Stop proxy pool
        if self.proxy_pool:
            await self.proxy_pool.stop()
        
    async def _process_successful_result(self, result: ProxyResult):
        """Process successful result - transform and store"""
        try:
            # Transform data
            transformed_records = await self.transformer.transform_odata_response(
                result.command.entity_set,
                result.data
            )
            
            if transformed_records:
                # Store processed data locally
                success = await self.local_storage.store_processed_records(
                    result.command.entity_set,
                    transformed_records
                )
                
                if success:
                    self.stats.records_stored += len(transformed_records)
                
                # Store raw data locally
                await self.local_storage.store_raw_response(
                    result.command.entity_set,
                    result.command.command_id,
                    result.data
                )
            
            self.stats.records_processed += len(transformed_records)
            
            # Handle pagination
            if result.next_link:
                next_command = self.plan_generator.create_next_page_command(
                    result.command, result.next_link
                )
                await self.proxy_pool.add_command(next_command)
            
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
                           command_id=result.command.command_id,
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
                # Use local constants instead of importing from module
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
        """Cleanup resources"""
        logger.info("Cleaning up connector resources")
        
        if self.proxy_pool and self.proxy_pool.is_running:
            await self.proxy_pool.stop()
            
            
        #edhi just prometheus push gateway kosam
        await self._push_metrics_to_gateway()
    
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
