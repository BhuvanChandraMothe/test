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
from planning.plan_generator import PlanGenerator, FetchCommand
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
            
            # Add health checks
            self._setup_health_checks()
            
            logger.info("Connector initialization completed")
            
        except Exception as e:
            logger.error("Failed to initialize connector", error=str(e))
            raise
    
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
        
        while self.is_running:
            # Update metrics
            if self.metrics and self.proxy_pool:
                pool_stats = self.proxy_pool.get_pool_stats()
                self.metrics.update_queue_size(pool_stats['queue_size'])
                self.metrics.update_active_workers(pool_stats['active_workers'])
            
            # Check if execution is complete
            if self.proxy_pool.get_queue_size() == 0:
                # Wait a bit more to ensure all workers are done
                await asyncio.sleep(2)
                if self.proxy_pool.get_queue_size() == 0:
                    break
            
            # Progress update callback
            if self.on_progress_update:
                progress_info = {
                    'queue_size': self.proxy_pool.get_queue_size(),
                    'completed_entities': len(completed_entities),
                    'records_processed': self.stats.records_processed,
                    'commands_executed': self.stats.commands_executed,
                    'commands_failed': self.stats.commands_failed
                }
                self.on_progress_update(progress_info)
            
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
    
    def _handle_proxy_error(self, result: ProxyResult):
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
                asyncio.create_task(self.proxy_pool.add_command(retry_command))
                logger.info("Command scheduled for retry", 
                           command_id=result.command.command_id,
                           retry_count=retry_command.retry_count)
            else:
                # Add to dead letter queue
                asyncio.create_task(
                    self.dead_letter_queue.add_failed_command(
                        result.command,
                        failure_type,
                        result.error or "Unknown error"
                    )
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
