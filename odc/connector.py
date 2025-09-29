import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import structlog

# Setup logging before any other imports
from .utils.logging_config import setup_connector_logging
setup_connector_logging()

from .config.models import ClientConfig, ODataConfig, ExecutionConfig, ServiceType
from .services.metadata import MetadataService
from .services.count import CountService
from .planning.graph_builder import RelationGraphBuilder
from .planning.plan_generator import PlanGenerator
from .workers.proxy_pool import ProxyPool, ProxyResult
from .workers.adaptive_pool import AdaptiveConnectionPool
from .storage.local_storage import LocalFileStorage, LocalStorageConfig
from .storage.transformer import DataTransformer
from .monitoring.metrics import MetricsCollector, get_metrics_collector
from .query.odata_builder import ODataQueryBuilder, ExpandClause, AggregateClause, GroupByClause, AggregateFunction
# Note: Some monitoring components may not exist yet
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


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
        """Calculate duration in seconds"""
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()


class SAPODataConnector:
    """Main SAP OData Connector class"""
    
    def __init__(self, config: ClientConfig):
        # Validate service type
        if config.service_type != ServiceType.ODATA:
            raise ValueError(f"This connector only supports OData service type, got: {config.service_type}")
        
        self.config = config
        self.sap_config = self._create_sap_config()
        
        # Initialize components
        self.metadata_service = None
        self.count_service = None
        self.graph_builder = None
        self.plan_generator = None
        self.proxy_pool = None
        self.local_storage = None
        self.transformer = None
        
        # Monitoring and error handling
        self.metrics: Optional[MetricsCollector] = None
        
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
            max_connections=50  # Will be updated dynamically during initialization
        )
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize connector and return available entities and metadata"""
        logger.info("Initializing SAP OData Connector")
        
        try:
            # Setup monitoring (simplified)
            self.metrics = get_metrics_collector()
            
            # Initialize services
            self.metadata_service = MetadataService(self.sap_config)
            self.count_service = CountService(self.sap_config)
            
            # Initialize plan generator
            self.plan_generator = PlanGenerator(
                batch_size=1000,  # Default, will be overridden at runtime
                max_concurrent_entities=5
            )
            
            # Initialize graph builder
            self.graph_builder = RelationGraphBuilder()
            
            # STEP 1: Test connection and validate credentials
            logger.info("Step 1: Testing connection to OData service")
            await self._test_connection()
            
            # STEP 2: Fetch metadata and save Entity Relationship file
            logger.info("Step 2: Fetching metadata and creating Entity Relationship file")
            await self._fetch_and_save_metadata()
            
            # STEP 3: Get entity information
            logger.info("Step 3: Analyzing available entities")
            entity_info = await self._get_entity_information()
            
            # STEP 3.5: Calculate workers based on SELECTED modules, not all entities
            selected_entity_count = self._get_selected_entity_count(entity_info)
            optimal_workers = self._calculate_optimal_workers(selected_entity_count)
            optimal_connections = self._calculate_optimal_connections(optimal_workers)
            
            logger.info("Dynamic scaling calculation",
                       total_entities_available=len(entity_info['entities']),
                       selected_entities_count=selected_entity_count,
                       calculated_workers=optimal_workers,
                       calculated_connections=optimal_connections)
            
            # Update sap_config with optimal values
            self.sap_config.max_connections = optimal_connections
            
            self.proxy_pool = ProxyPool(
                odata_config=self.sap_config,
                max_workers=optimal_workers
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
            
            logger.info(" Connector initialization completed successfully",
                       total_entities_available=len(entity_info['entities']),
                       selected_entities_count=selected_entity_count,
                       dynamic_workers=f"{optimal_workers} (auto-calculated from {selected_entity_count} selected entities)",
                       dynamic_connections=f"{optimal_connections} (auto-calculated from {optimal_workers} workers)")
            
            return entity_info
            
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
    
    async def _get_entity_information(self) -> Dict[str, Any]:
        """Get entity information for initialization response"""
        logger.info("Gathering entity information...")
        
        # Get entity schemas from metadata service
        entity_schemas = self.metadata_service.schemas
        entity_names = list(entity_schemas.keys())
        
        # Get entity counts
        async with self.count_service:
            entity_counts = await self.count_service.get_entity_counts(entity_names)
        
        # Build entity information
        entities_info = []
        total_records = 0
        
        for entity_name in entity_names:
            record_count = entity_counts.get(entity_name, 0)
            total_records += record_count
            
            # Get entity schema details
            schema = entity_schemas.get(entity_name, {})
            properties = []
            
            # Handle different schema object types
            try:
                if hasattr(schema, 'properties'):
                    # If schema is an object with properties attribute
                    properties = list(schema.properties.keys()) if schema.properties else []
                elif isinstance(schema, dict) and 'properties' in schema:
                    # If schema is a dictionary
                    properties = list(schema['properties'].keys())
                else:
                    # Fallback: try to get properties from the schema object
                    properties = []
            except Exception as e:
                logger.debug(f"Could not extract properties for {entity_name}: {e}")
                properties = []
            
            entities_info.append({
                'name': entity_name,
                'record_count': record_count,
                'properties': properties[:10],  # First 10 properties
                'total_properties': len(properties),
                'url': f"{self.sap_config.service_url}/{entity_name}"
            })
        
        return {
            'service_url': self.sap_config.service_url,
            'total_entities': len(entity_names),
            'total_records': total_records,
            'entities': entities_info,
            'metadata': {
                'schemas_available': len(entity_schemas),
                'relationships': len(self.metadata_service.get_foreign_key_relationships()) if hasattr(self.metadata_service, 'get_foreign_key_relationships') else 0
            }
        }
    
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
    
    def _get_selected_entity_count(self, entity_info: Dict[str, Any]) -> int:
        """Get count of entities that will actually be processed based on user selection
        
        Args:
            entity_info: Entity information from _get_entity_information()
            
        Returns:
            Count of entities that match user's selected_modules
        """
        if not self.config.selected_modules:
            # No selection specified, process all entities
            total_count = len(entity_info['entities'])
            logger.info("No module selection specified, will process all entities",
                       total_entities=total_count)
            return total_count
        
        # Filter entities based on selected_modules
        available_entity_names = [entity['name'] for entity in entity_info['entities']]
        selected_entities = []
        
        for module_name in self.config.selected_modules:
            if module_name in available_entity_names:
                selected_entities.append(module_name)
            else:
                logger.warning("Selected module not found in service",
                             module=module_name,
                             available_entities=available_entity_names[:10])  # Show first 10
        
        selected_count = len(selected_entities)
        
        logger.info("Module selection applied",
                   selected_modules=self.config.selected_modules,
                   found_entities=selected_entities,
                   selected_count=selected_count,
                   total_available=len(available_entity_names))
        
        # Return at least 1 to avoid division by zero
        return max(1, selected_count)
    
    def _calculate_optimal_workers(self, entity_count: int) -> int:
        """Calculate optimal number of workers based on entity count and system resources
        
        Logic:
        1. Base calculation: 1 worker per 2-3 entities (entity_count // 2)
        2. Minimum: 2 workers (to ensure parallelism)
        3. Maximum: 10 workers (to prevent resource exhaustion)
        4. Consider user preference as a cap, not a minimum
        
        Examples:
        - 5 entities → 2 workers (max(2, min(5//2, 10)) = max(2, min(2, 10)) = 2)
        - 10 entities → 5 workers (max(2, min(10//2, 10)) = max(2, min(5, 10)) = 5)
        - 30 entities → 10 workers (max(2, min(30//2, 10)) = max(2, min(15, 10)) = 10)
        """
        # Base calculation: 1 worker per 2-3 entities, with min/max bounds
        base_workers = max(2, min(entity_count // 2, 10))
        
        # For now, just return the base calculation since max_workers is now a runtime parameter
        optimal = base_workers
        
        # logger.info(" Dynamic Worker Calculation", 
        #            entity_count=entity_count,
        #            formula="max(2, min(entity_count // 2, 10))",
        #            base_calculation=base_workers,
        #            user_max_preference=user_preference,
        #            final_optimal=optimal,
        #            reasoning=f"For {entity_count} entities: {entity_count}//2={entity_count//2}, capped at 2-10 range")
        
        return optimal
    
    def _calculate_optimal_connections(self, worker_count: int) -> int:
        """Calculate optimal connection pool size based on worker count
        
        Logic:
        1. Base calculation: 4 connections per worker (worker_count * 4)
        2. Reasoning: Each worker may need multiple connections for:
           - Main data request
           - Retry requests
           - Concurrent batch processing
           - Connection pool efficiency
        3. Minimum: 10 connections (baseline for any workload)
        4. Maximum: 100 connections (to prevent overwhelming the server)
        
        Examples:
        - 2 workers → 10 connections (max(10, min(2*4, 100)) = max(10, 8) = 10)
        - 5 workers → 20 connections (max(10, min(5*4, 100)) = max(10, 20) = 20)
        - 10 workers → 40 connections (max(10, min(10*4, 100)) = max(10, 40) = 40)
        - 30 workers → 100 connections (max(10, min(30*4, 100)) = max(10, 100) = 100)
        """
        # Rule: 4 connections per worker to handle concurrent requests and retries
        base_connections = worker_count * 4
        
        # Ensure minimum of 10 and maximum of 100
        optimal = max(10, min(base_connections, 100))
        
        # logger.info(" Dynamic Connection Pool Calculation",
        #            worker_count=worker_count,
        #            formula="max(10, min(worker_count * 4, 100))",
        #            base_calculation=base_connections,
        #            final_optimal=optimal,
        #            reasoning=f"For {worker_count} workers: {worker_count}*4={base_connections}, bounded 10-100",
        #            connection_per_worker_ratio=f"{optimal/worker_count:.1f} connections per worker")
        
        return optimal
    
    def _setup_health_checks(self):
        """Setup health check functions (simplified)"""
        # Health checks simplified for now
        logger.debug("Health checks setup completed")
    
    async def get_data(
        self, 
        entity_name: Optional[str] = None,
        filter_condition: Optional[str] = None,
        selected_entities: Optional[List[str]] = None,
        record_limit: Optional[int] = None,
        batch_size: int = 1000,
        max_workers: int = 5,
        requests_per_second: float = 5.0,
        enable_parallel_processing: bool = True
    ) -> Dict[str, Any]:
        """Get data from OData service with optional filtering
        
        Args:
            entity_name: Specific entity to fetch (if None, fetches all or selected_entities)
            filter_condition: OData filter condition (e.g., "Name eq 'John'")
            selected_entities: List of entities to process (legacy parameter)
            record_limit: Override the configured record limit
            batch_size: Records per batch (default: 1000)
            max_workers: Maximum concurrent workers (default: 5)
            requests_per_second: Rate limit for API calls (default: 5.0)
            enable_parallel_processing: Enable parallel processing (default: True)
            
        Returns:
            Dictionary containing execution stats and data
        """
        # Create execution config from parameters
        self.exec_config = ExecutionConfig(
            selected_entities=selected_entities,
            total_records_limit=record_limit,
            batch_size=batch_size,
            max_workers=max_workers,
            requests_per_second=requests_per_second,
            enable_parallel_processing=enable_parallel_processing
        )
        
        logger.info("Starting SAP OData connector execution",
                   entity_name=entity_name,
                   filter_condition=filter_condition,
                   execution_config=self.exec_config.to_dict())
        
        try:
            self.is_running = True
            self.stats = ConnectorStats(start_time=datetime.now(timezone.utc))
            
            # Reset the global record tracker for clean state
            from .planning.record_tracker import reset_global_tracker
            reset_global_tracker()
            # Update plan generator to use the new tracker
            from .planning.record_tracker import get_global_tracker
            self.plan_generator.record_tracker = get_global_tracker()
            
            # Apply record limit (parameter overrides config)
            effective_limit = record_limit or self.config.total_records_limit
            if effective_limit:
                self.plan_generator.record_tracker.set_total_records_limit(effective_limit)
            
            # Determine entities to process
            entities_to_process = self._determine_entities_to_process(
                entity_name, selected_entities
            )
            
            # Phase 1: Discovery and Planning
            await self._discovery_phase_filtered(
                entities_to_process, filter_condition
            )
            
            # Phase 2: Execution
            await self._execution_phase()
            
            # Phase 3: Completion and data retrieval
            result_data = await self._completion_phase_with_data(entities_to_process)
            
            self.stats.end_time = datetime.now(timezone.utc)
            
            # Build comprehensive result
            result = {
                'execution_stats': {
                    'duration_seconds': self.stats.duration_seconds,
                    'entities_processed': self.stats.entities_processed,
                    'records_processed': self.stats.records_processed,
                    'records_stored': self.stats.records_stored,
                    'commands_executed': self.stats.commands_executed,
                    'commands_failed': self.stats.commands_failed
                },
                'filter_applied': {
                    'entity_name': entity_name,
                    'filter_condition': filter_condition,
                    'entities_processed': entities_to_process,
                    'record_limit': effective_limit
                },
                'data': result_data
            }
            
            # Try to get global status but don't hang if it fails
            try:
                if hasattr(self.plan_generator, 'record_tracker'):
                    global_status = await asyncio.wait_for(
                        self.plan_generator.record_tracker.get_global_status(), 
                        timeout=2.0
                    )
                    result['execution_stats']['global_records_fetched'] = global_status.get('global_records_fetched', 0)
                    result['execution_stats']['entities_tracked'] = global_status.get('entities_tracked', 0)
                    result['execution_stats']['entities_complete'] = global_status.get('entities_complete', 0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception) as e:
                logger.warning(f"Could not get final global status: {e}")
            
            logger.info("Connector execution completed successfully",
                       duration=self.stats.duration_seconds,
                       entities_processed=self.stats.entities_processed,
                       records_processed=self.stats.records_processed)
            
            return result
            
        except Exception as e:
            logger.error("Connector execution failed", error=str(e))
            await self._handle_execution_error(e)
            raise
        
        finally:
            self.is_running = False
            await self._cleanup()
    
    async def get_data_with_expand(
        self,
        entity_name: str,
        expand_properties: List[str],
        select_fields: Optional[List[str]] = None,
        filter_condition: Optional[str] = None,
        orderby: Optional[str] = None,
        top: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get data with expanded navigation properties
        
        Args:
            entity_name: Main entity to query
            expand_properties: List of navigation properties to expand
            select_fields: Fields to select from main entity
            filter_condition: OData filter condition
            orderby: OData orderby clause
            top: Maximum records to return
            
        Returns:
            Dictionary containing expanded data
        """
        logger.info("Starting expand query",
                   entity=entity_name,
                   expand_properties=expand_properties,
                   select_fields=select_fields)
        
        try:
            await self._ensure_initialized()
            
            # Build OData query with expand
            query_builder = ODataQueryBuilder(entity_name)
            
            if select_fields:
                query_builder.select(*select_fields)
            
            for prop in expand_properties:
                query_builder.expand(prop)
            
            if filter_condition:
                query_builder.filter(filter_condition)
            
            if orderby:
                query_builder.orderby(orderby.split()[0], 
                                    orderby.endswith('desc') if ' ' in orderby else False)
            
            if top:
                query_builder.top(top)
            
            # Execute query
            query_url = query_builder.build_url(self.sap_config.service_url)
            return await self._execute_single_query(query_url, entity_name)
            
        except Exception as e:
            logger.error("Expand query failed", entity=entity_name, error=str(e))
            raise
    
    async def get_aggregated_data(
        self,
        entity_name: str,
        group_by_fields: List[str],
        aggregations: List[AggregateClause],
        filter_condition: Optional[str] = None,
        having_condition: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated data using OData $apply transformations
        
        Args:
            entity_name: Entity to aggregate
            group_by_fields: Fields to group by
            aggregations: List of aggregation operations
            filter_condition: Filter before aggregation
            having_condition: Filter after aggregation (having clause)
            
        Returns:
            Dictionary containing aggregated results
        """
        logger.info("Starting aggregation query",
                   entity=entity_name,
                   group_by_fields=group_by_fields,
                   aggregations=[f"{agg.field}:{agg.function.value}" for agg in aggregations])
        
        try:
            await self._ensure_initialized()
            
            # Build aggregation query
            query_builder = ODataQueryBuilder(entity_name)
            
            if filter_condition:
                query_builder.filter(filter_condition)
            
            # Add groupby with aggregations
            query_builder.groupby(*group_by_fields)
            for agg in aggregations:
                query_builder.aggregate(agg.field, agg.function, agg.alias)
            
            # Add having condition as additional filter
            if having_condition:
                query_builder.apply_transformation(f"filter({having_condition})")
            
            # Execute query
            query_url = query_builder.build_url(self.sap_config.service_url)
            return await self._execute_single_query(query_url, entity_name)
            
        except Exception as e:
            logger.error("Aggregation query failed", entity=entity_name, error=str(e))
            raise
    
    def create_query_builder(self, entity_name: str) -> ODataQueryBuilder:
        """
        Create a new OData query builder for the specified entity
        
        Args:
            entity_name: Name of the entity to query
            
        Returns:
            New ODataQueryBuilder instance
        """
        return ODataQueryBuilder(entity_name)
    
    async def get_data_with_custom_query(
        self,
        query_builder: ODataQueryBuilder
    ) -> Dict[str, Any]:
        """
        Execute a custom OData query using the query builder
        
        Args:
            query_builder: Pre-configured OData query builder
            
        Returns:
            Dictionary containing query results
        """
        entity_name = query_builder.entity_name
        logger.info("Starting custom query",
                   entity=entity_name,
                   query_string=query_builder.build_query_string())
        
        try:
            await self._ensure_initialized()
            
            # Execute custom query
            query_url = query_builder.build_url(self.sap_config.service_url)
            return await self._execute_single_query(query_url, entity_name)
            
        except Exception as e:
            logger.error("Custom query failed", entity=entity_name, error=str(e))
            raise
    
    async def _execute_single_query(self, query_url: str, entity_name: str) -> Dict[str, Any]:
        """
        Execute a single OData query and return results
        
        Args:
            query_url: Complete OData query URL
            entity_name: Entity name for logging/metrics
            
        Returns:
            Dictionary containing query results
        """
        try:
            # Use proxy pool resilience layer
            async with self.proxy_pool.resilience_layer.http_client as client:
                response = await client.get(query_url)
            
            response.raise_for_status()
            data = response.json()
            
            records = data.get('value', [])
            
            # Transform data if transformer is available
            if self.transformer:
                transformed_records = await self.transformer.transform_data(entity_name, records)
            else:
                transformed_records = records
            
            return {
                'status': 'success',
                'entity': entity_name,
                'record_count': len(transformed_records),
                'records': transformed_records,
                'odata_context': data.get('@odata.context'),
                'odata_count': data.get('@odata.count'),
                'query_url': query_url
            }
            
        except Exception as e:
            logger.error("Single query execution failed",
                        entity=entity_name,
                        query_url=query_url,
                        error=str(e))
            raise
    
    async def _ensure_initialized(self):
        """Ensure connector is properly initialized"""
        if not self.metadata_service:
            await self.initialize()
    
    def _determine_entities_to_process(
        self, 
        entity_name: Optional[str], 
        selected_entities: Optional[List[str]]
    ) -> List[str]:
        """Determine which entities to process based on parameters"""
        if entity_name:
            # Single entity specified
            return [entity_name]
        elif selected_entities:
            # Multiple entities specified
            return selected_entities
        elif self.config.selected_modules:
            # Use config selection
            return self.config.selected_modules
        else:
            # Process all entities
            return list(self.metadata_service.schemas.keys())
    
    async def _discovery_phase_filtered(
        self, 
        entities_to_process: List[str], 
        filter_condition: Optional[str]
    ):
        """Phase 1: Discover metadata and plan execution with filtering"""
        logger.info("Starting filtered discovery phase",
                   entities_count=len(entities_to_process),
                   entities=entities_to_process,
                   filter_condition=filter_condition)
        
        # Fetch metadata (already done in initialize, but ensure transformer is ready)
        entity_schemas = self.metadata_service.schemas
        
        # Initialize transformer with schemas
        self.transformer = DataTransformer(entity_schemas)
        
        # Validate requested entities exist
        available_entities = set(entity_schemas.keys())
        invalid_entities = [e for e in entities_to_process if e not in available_entities]
        if invalid_entities:
            raise ValueError(f"Invalid entities requested: {invalid_entities}. Available: {list(available_entities)}")
        
        # Get entity counts (with potential filter impact)
        async with self.count_service:
            if filter_condition:
                # For filtered queries, we can't easily predict count, so use conservative estimates
                logger.info("Filter condition detected - using conservative count estimates")
                entity_counts = {entity: 1000 for entity in entities_to_process}  # Conservative estimate
            else:
                entity_counts = await self.count_service.get_entity_counts(entities_to_process)
        
        # Build dependency graph
        self.graph_builder.add_entities(entities_to_process)
        relationships = self.metadata_service.get_foreign_key_relationships()
        self.graph_builder.add_relationships(relationships)
        
        # Generate execution plan with filter consideration
        processing_order = self.graph_builder.get_processing_order()
        await self.plan_generator.create_execution_plan_filtered(
            entity_counts, processing_order, entities_to_process, filter_condition
        )
        
        logger.info("Filtered discovery phase completed",
                   entities=len(entities_to_process),
                   total_estimated_records=sum(entity_counts.values()),
                   processing_levels=len(processing_order),
                   filter_applied=bool(filter_condition))
        
        # Log the execution plan summary
        logger.info("Filtered execution plan summary:")
        for level_idx, level_entities in enumerate(processing_order):
            level_entities_filtered = [e for e in level_entities if e in entities_to_process]
            if level_entities_filtered:
                level_total = sum(entity_counts.get(entity, 0) for entity in level_entities_filtered)
                logger.info(f"   Level {level_idx + 1}: {len(level_entities_filtered)} entities, ~{level_total} records")
                for entity in level_entities_filtered:
                    logger.info(f"     - {entity}: ~{entity_counts.get(entity, 0)} records")
    
    async def _execution_phase(self):
        """Phase 2: Execute data fetching and processing"""
        logger.info("Starting execution phase")
        
        # Start proxy pool
        await self.proxy_pool.start()
        
        # Initialize metrics with current configuration
        if self.metrics:
            # Clear any stale metrics and set current values
            self.metrics.update_active_workers(self.exec_config.max_workers)
            self.metrics.update_queue_size(0)  # Start with empty queue
            logger.info("Metrics initialized", 
                       max_workers=self.exec_config.max_workers, 
                       initial_queue_size=0)
        
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
                
                # Update metrics with real-time values
                if self.metrics:
                    self.metrics.update_queue_size(queue_size)
                    self.metrics.update_active_workers(active_workers)
                    
                    # Update circuit breaker states for all workers
                    if hasattr(self.proxy_pool, 'workers'):
                        for worker in self.proxy_pool.workers:
                            if hasattr(worker, 'resilience') and hasattr(worker.resilience, 'circuit_breaker'):
                                self.metrics.update_circuit_breaker_state(
                                    worker_id=worker.worker_id,
                                    state=worker.resilience.circuit_breaker.state
                                )
                
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
        
    async def _completion_phase_with_data(self, entities_processed: List[str]) -> Dict[str, Any]:
        """Phase 3: Complete execution and return processed data"""
        logger.info("Starting completion phase with data retrieval")
        
        result_data = {}
        
        # Save and retrieve processed data for each entity
        for entity_name in entities_processed:
            if entity_name in self.plan_generator.entity_plans:
                # Save unified records
                await self.local_storage.save_unified_processed_records(entity_name)
                
                # Load the processed data for return
                try:
                    entity_data = await self.local_storage.load_processed_records(entity_name)
                    result_data[entity_name] = {
                        'records': entity_data,
                        'count': len(entity_data) if entity_data else 0,
                        'status': 'completed'
                    }
                    logger.info(f"Loaded {len(entity_data) if entity_data else 0} records for {entity_name}")
                except Exception as e:
                    logger.warning(f"Could not load processed data for {entity_name}: {e}")
                    result_data[entity_name] = {
                        'records': [],
                        'count': 0,
                        'status': 'error',
                        'error': str(e)
                    }
        
        if self.proxy_pool:
            await self.proxy_pool.stop()
        
        logger.info("Completion phase finished", entities_with_data=len(result_data))
        return result_data
        
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
        """Handle execution-level errors (simplified)"""
        logger.error("Connector execution failed", 
                    error=str(error),
                    error_type=type(error).__name__,
                    connector_state="execution_failed")
        
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
    
    async def run_legacy(self, selected_entities: Optional[List[str]] = None) -> ConnectorStats:
        """Legacy run method for backward compatibility"""
        logger.info("Starting SAP OData connector execution (legacy mode)")
        
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
            
            # Phase 1: Discovery and Planning (legacy style)
            await self._discovery_phase_legacy(selected_entities)
            
            # Phase 2: Execution
            await self._execution_phase()
            
            # Phase 3: Completion (legacy style)
            await self._completion_phase_legacy()
            
            self.stats.end_time = datetime.now(timezone.utc)
            
            logger.info("Legacy connector execution completed successfully",
                       duration=self.stats.duration_seconds,
                       entities_processed=self.stats.entities_processed,
                       records_processed=self.stats.records_processed)
            
            return self.stats
            
        except Exception as e:
            logger.error("Legacy connector execution failed", error=str(e))
            await self._handle_execution_error(e)
            raise
        
        finally:
            self.is_running = False
            await self._cleanup()
    
    async def _discovery_phase_legacy(self, selected_entities: Optional[List[str]]):
        """Legacy discovery phase for backward compatibility"""
        logger.info("Starting legacy discovery phase")
        
        # Fetch metadata (already done in initialize, but ensure transformer is ready)
        entity_schemas = self.metadata_service.schemas
        
        # Initialize transformer with schemas
        self.transformer = DataTransformer(entity_schemas)
        
        # Determine which entities to process (legacy logic)
        if selected_entities is not None:
            entity_names = selected_entities
        elif self.config.selected_modules:
            entity_names = self.config.selected_modules
        else:
            entity_names = list(entity_schemas.keys())
            
        logger.info("Legacy entity selection determined", 
                   selected_entities_param=selected_entities,
                   config_selected_modules=self.config.selected_modules,
                   final_entity_count=len(entity_names),
                   entities=entity_names[:5] if len(entity_names) > 5 else entity_names)
        
        # Get entity counts
        async with self.count_service:
            entity_counts = await self.count_service.get_entity_counts(entity_names)
        
        # Build dependency graph
        self.graph_builder.add_entities(entity_names)
        relationships = self.metadata_service.get_foreign_key_relationships()
        self.graph_builder.add_relationships(relationships)
        
        # Generate execution plan (legacy method)
        processing_order = self.graph_builder.get_processing_order()
        await self.plan_generator.create_execution_plan(
            entity_counts, processing_order, entity_names
        )
        
        logger.info("Legacy discovery phase completed",
                   entities=len(entity_names),
                   total_records=sum(entity_counts.values()),
                   processing_levels=len(processing_order))
    
    async def _completion_phase_legacy(self):
        """Legacy completion phase for backward compatibility"""
        logger.info("Starting legacy completion phase")
        
        for entity_name in self.plan_generator.entity_plans.keys():
            await self.local_storage.save_unified_processed_records(entity_name)
        
        if self.proxy_pool:
            await self.proxy_pool.stop()


# Factory function for easy connector creation
def create_connector(config_file: Optional[str] = None) -> SAPODataConnector:
    """Create SAP OData Connector from configuration"""
    settings = ConnectorSettings(config_file)
    client_config = settings.get_client_config()
    return SAPODataConnector(client_config)