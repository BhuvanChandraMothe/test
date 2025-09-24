"""Proxy pool implementation for SAP OData connector"""

import asyncio
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass
import structlog
from urllib.parse import urlencode
import httpx

from config.models import ODataConfig
from workers.resilience import ResilienceComponents
from monitoring.metrics import get_metrics_collector
logger = structlog.get_logger(__name__)

# Import these at runtime to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..planning.plan_generator import FetchCommand, CommandType
    from ..planning.record_tracker import GlobalRecordTracker


@dataclass
class ProxyResult:
    """Result from a proxy worker execution"""
    command: 'FetchCommand'  # Forward reference to avoid circular import
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    next_link: Optional[str] = None
    retry_after: Optional[int] = None


class ProxyWorker:
    """Individual proxy worker with resilience patterns"""
    
    def __init__(
        self,
        worker_id: str,
        odata_config: ODataConfig,
        resilience: ResilienceComponents
    ):
        self.worker_id = worker_id
        self.odata_config = odata_config
        self.resilience = resilience
        self.is_running = False
        # Import at runtime to avoid circular imports
        from planning.record_tracker import get_global_tracker
        self.record_tracker = get_global_tracker()
        self._stats = {
            'requests_processed': 0,
            'requests_failed': 0,
            'requests_retried': 0
        }
    
    async def execute(self, command: 'FetchCommand') -> ProxyResult:
        """Execute a fetch command"""
        start_time = asyncio.get_event_loop().time()
        
        logger.info("🚀 Worker starting command execution", 
                   worker_id=self.worker_id,
                   command_id=command.command_id,
                   entity=command.entity_set,
                   command_type=command.command_type.value,
                   skip=command.skip,
                   top=command.top,
                   priority=command.priority.value,
                   retry_count=command.retry_count)
        
        try:
            # Apply rate limiting
            logger.debug("⏳ Worker waiting for rate limit token", 
                        worker_id=self.worker_id,
                        command_id=command.command_id)
            
            await self.resilience.token_bucket.acquire()
            
            logger.debug("✅ Worker acquired rate limit token", 
                        worker_id=self.worker_id,
                        command_id=command.command_id)
            
            # Execute with circuit breaker and retry
            logger.info("🔄 Worker executing request with resilience patterns", 
                       worker_id=self.worker_id,
                       command_id=command.command_id,
                       circuit_breaker_state=self.resilience.circuit_breaker.state)
            
            result = await self._execute_with_circuit_breaker(command)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            self._stats['requests_processed'] += 1
            
            # Record detailed metrics for successful requests
            metrics = get_metrics_collector()
            metrics.record_request(
                entity=command.entity_set,
                worker_id=self.worker_id,
                duration=execution_time,
                success=True
            )
            
            # Record processed records count
            if result.data and 'value' in result.data:
                record_count = len(result.data['value'])
                metrics.record_records_processed(
                    entity=command.entity_set,
                    count=record_count,
                    success=True
                )
            
            logger.info("✅ Worker completed command successfully", 
                       worker_id=self.worker_id,
                       command_id=command.command_id,
                       entity=command.entity_set,
                       execution_time_seconds=round(execution_time, 2),
                       has_next_page=bool(result.next_link),
                       records_fetched=len(result.data.get('value', [])) if result.data else 0)
            
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self._stats['requests_failed'] += 1
            
            # Record detailed metrics for failed requests
            metrics = get_metrics_collector()
            metrics.record_request(
                entity=command.entity_set,
                worker_id=self.worker_id,
                duration=execution_time,
                success=False,
                error_type=type(e).__name__
            )
            
            logger.error("❌ Worker command execution failed",
                        worker_id=self.worker_id,
                        command_id=command.command_id,
                        entity=command.entity_set,
                        execution_time_seconds=round(execution_time, 2),
                        error=str(e),
                        error_type=type(e).__name__)
            
            return ProxyResult(
                command=command,
                success=False,
                error=str(e)
            )
    
    async def _execute_with_circuit_breaker(self, command: 'FetchCommand') -> ProxyResult:
        """Execute command with circuit breaker protection"""
        # Temporarily bypass circuit breaker for debugging
        return await self._make_http_request(command)
    
    async def _make_http_request(self, command: 'FetchCommand') -> ProxyResult:
        """Make the actual HTTP request to OData API"""
        # Check if we should still fetch more records for this entity
        should_fetch = await self.record_tracker.should_create_more_commands(command.entity_set)
        if not should_fetch:
            logger.info("🛑 Skipping request - record limit reached", 
                       worker_id=self.worker_id,
                       command_id=command.command_id,
                       entity=command.entity_set)
            return ProxyResult(
                command=command,
                success=True,
                data={'value': []},  # Empty result
                next_link=None
            )
        
        # Calculate optimal batch size to avoid overfetching
        optimal_top = await self.record_tracker.calculate_optimal_batch_size(
            command.entity_set, 
            command.top
        )
        
        # Update command with optimal batch size if different
        if optimal_top != command.top:
            logger.info("📏 Adjusted batch size for optimal fetching",
                       worker_id=self.worker_id,
                       command_id=command.command_id,
                       entity=command.entity_set,
                       original_top=command.top,
                       optimal_top=optimal_top)
            
            # Create new URL params with adjusted $top
            adjusted_params = command.url_params.copy()
            adjusted_params['$top'] = str(optimal_top)
        else:
            adjusted_params = command.url_params
        
        client = await self.resilience.connection_pool.get_client()
        
        # Build URL
        url = self.odata_config.entity_set_url(command.entity_set)
        if adjusted_params:
            url += f"?{urlencode(adjusted_params)}"
        
        logger.debug("🌐 Worker making HTTP request", 
                    worker_id=self.worker_id,
                    command_id=command.command_id,
                    url=url,
                    method="GET")
        
        # Get authentication
        auth_header = await self._get_auth_header()
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        headers.update(auth_header)
        
        try:
            response = await client.get(url, headers=headers)
            
            logger.debug("📡 Worker received HTTP response", 
                        worker_id=self.worker_id,
                        command_id=command.command_id,
                        status_code=response.status_code,
                        response_size=len(response.content) if response.content else 0)
            
            # Handle different response codes
            if response.status_code == 200:
                data = response.json()
                next_link = self._extract_next_link(data)
                
                record_count = 0
                if 'value' in data:
                    record_count = len(data['value'])
                elif 'd' in data and 'results' in data['d']:
                    record_count = len(data['d']['results'])
                
                # Record page completion with the tracker
                page_num = (command.skip // command.top) + 1
                tracking_result = await self.record_tracker.record_page_completion(
                    command.entity_set, 
                    page_num, 
                    record_count
                )
                
                # Check if we should suppress next_link due to limits
                if tracking_result.get("global_limit_reached") or tracking_result.get("entity_complete"):
                    next_link = None  # Stop pagination
                    logger.info("🎯 Stopping pagination due to record limits", 
                               worker_id=self.worker_id,
                               command_id=command.command_id,
                               entity=command.entity_set,
                               global_limit_reached=tracking_result.get("global_limit_reached"),
                               entity_complete=tracking_result.get("entity_complete"))
                
                logger.info("📊 Worker successfully fetched data", 
                           worker_id=self.worker_id,
                           command_id=command.command_id,
                           entity=command.entity_set,
                           records_in_response=record_count,
                           actual_records_added=tracking_result.get("actual_records_added", record_count),
                           entity_total_fetched=tracking_result.get("entity_records_fetched", 0),
                           global_total_fetched=tracking_result.get("global_records_fetched", 0),
                           has_next_page=bool(next_link))
                
                return ProxyResult(
                    command=command,
                    success=True,
                    data=data,
                    next_link=next_link
                )
            
            elif response.status_code == 429:
                # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning("⚠️ Worker rate limited by server",
                             worker_id=self.worker_id,
                             command_id=command.command_id,
                             retry_after=retry_after)
                
                return ProxyResult(
                    command=command,
                    success=False,
                    error="Rate limited",
                    retry_after=retry_after
                )
            
            elif 400 <= response.status_code < 500:
                # Client error - don't retry
                error_msg = f"Client error {response.status_code}: {response.text}"
                logger.error("🚫 Worker encountered client error", 
                           worker_id=self.worker_id,
                           command_id=command.command_id,
                           status_code=response.status_code,
                           error=error_msg)
                
                return ProxyResult(
                    command=command,
                    success=False,
                    error=error_msg
                )
            
            else:
                # Server error - will be retried
                logger.warning("🔄 Worker encountered server error, will retry", 
                             worker_id=self.worker_id,
                             command_id=command.command_id,
                             status_code=response.status_code)
                response.raise_for_status()
                
        except httpx.HTTPError as e:
            logger.warning("🌐 Worker HTTP error occurred",
                         worker_id=self.worker_id,
                         command_id=command.command_id,
                         error=str(e),
                         error_type=type(e).__name__)
            raise
    
    async def _get_auth_header(self) -> Dict[str, str]:
        """Get authentication header"""
        if self.odata_config.client_id:
            # OAuth token
            token = await self.resilience.token_manager.get_valid_token()
            return {'Authorization': f'Bearer {token}'}
        elif self.odata_config.username and self.odata_config.password:
            # Basic auth
            import base64
            credentials = f"{self.odata_config.username}:{self.odata_config.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {'Authorization': f'Basic {encoded}'}
        else:
            # No authentication (for public services like Northwind)
            return {}
    
    def _extract_next_link(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract next page link from OData response"""
        # Check different possible locations for next link
        if 'd' in data:
            return data['d'].get('__next')
        
        return data.get('@odata.nextLink')
    
    def get_stats(self) -> Dict[str, int]:
        """Get worker statistics"""
        return self._stats.copy()


class ProxyPool:
    """Pool of proxy workers for concurrent execution"""
    
    def __init__(
        self,
        odata_config: ODataConfig,
        max_workers: int = 10,
        queue_maxsize: int = 1000
    ):
        self.odata_config = odata_config
        self.max_workers = max_workers
        self.queue: asyncio.Queue[FetchCommand] = asyncio.Queue(maxsize=queue_maxsize)
        self.result_queue: asyncio.Queue[ProxyResult] = asyncio.Queue()
        self.workers: List[ProxyWorker] = []
        self.worker_tasks: List[asyncio.Task] = []
        self.semaphore = asyncio.Semaphore(max_workers)
        self.is_running = False
        self.resilience = ResilienceComponents.create_default(odata_config)
        
        # Callbacks
        self.on_result: Optional[Callable[[ProxyResult], Awaitable[None]]] = None
        self.on_error: Optional[Callable[[ProxyResult], Awaitable[None]]] = None
    
    async def start(self):
        """Start the proxy pool"""
        if self.is_running:
            return
        
        logger.info("Starting proxy pool", max_workers=self.max_workers)
        
        # Create workers
        for i in range(self.max_workers):
            worker = ProxyWorker(
                worker_id=f"worker_{i}",
                odata_config=self.odata_config,
                resilience=self.resilience
            )
            self.workers.append(worker)
        
        # Start worker tasks
        for worker in self.workers:
            task = asyncio.create_task(self._worker_loop(worker))
            self.worker_tasks.append(task)
        
        # Start result processor
        self.result_processor_task = asyncio.create_task(self._process_results())
        
        self.is_running = True
        logger.info("Proxy pool started successfully")
    
    async def stop(self):
        """Stop the proxy pool"""
        if not self.is_running:
            return
        
        logger.info("Stopping proxy pool")
        
        self.is_running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Cancel result processor
        if hasattr(self, 'result_processor_task'):
            self.result_processor_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Cleanup resources
        await self.resilience.cleanup()
        
        logger.info("Proxy pool stopped")
    
    async def add_command(self, command: 'FetchCommand'):
        """Add a command to the processing queue"""
        try:
            await self.queue.put(command)
            logger.debug("Command added to queue", command_id=command.command_id)
        except asyncio.QueueFull:
            logger.warning("Queue is full, command rejected", command_id=command.command_id)
            raise
    
    async def add_commands(self, commands: List['FetchCommand']):
        """Add multiple commands to the processing queue"""
        for command in commands:
            await self.add_command(command)
        
        logger.info("Commands added to queue", count=len(commands))
    
    async def _worker_loop(self, worker: ProxyWorker):
        """Main loop for a proxy worker"""
        worker.is_running = True
        
        logger.info("🟢 Worker started and ready for commands", 
                   worker_id=worker.worker_id,
                   worker_status="ACTIVE")
        
        try:
            while self.is_running:
                try:
                    # Update active workers and queue size metrics
                    metrics = get_metrics_collector()
                    active_workers = sum(1 for w in self.workers if w.is_running)
                    metrics.update_active_workers(active_workers)
                    metrics.update_queue_size(self.queue.qsize())
                    
                    logger.debug("👀 Worker waiting for commands", 
                               worker_id=worker.worker_id,
                               worker_status="WAITING",
                               queue_size=self.queue.qsize())
                    
                    # Check if pool is still running before waiting
                    if not self.is_running:
                        break
                        
                    # Wait for command with timeout
                    command = await asyncio.wait_for(
                        self.queue.get(), timeout=1.0
                    )
                    
                    logger.info("📋 Worker picked up command from queue", 
                               worker_id=worker.worker_id,
                               worker_status="PROCESSING",
                               command_id=command.command_id,
                               entity=command.entity_set,
                               queue_size_after_pickup=self.queue.qsize())
                    
                    # Acquire semaphore for concurrency control
                    async with self.semaphore:
                        logger.debug("🔒 Worker acquired semaphore", 
                                   worker_id=worker.worker_id,
                                   command_id=command.command_id)
                        
                        result = await worker.execute(command)
                        await self.result_queue.put(result)
                        self.queue.task_done()
                        
                        logger.debug("🔓 Worker released semaphore", 
                                   worker_id=worker.worker_id,
                                   command_id=command.command_id)
                
                except asyncio.TimeoutError:
                    # No commands available - check if pool is still running
                    if not self.is_running:
                        logger.info("🛑 Worker exiting - pool stopped", 
                                   worker_id=worker.worker_id,
                                   worker_status="STOPPED")
                        break
                    logger.debug("⏰ Worker timeout waiting for commands", 
                               worker_id=worker.worker_id,
                               worker_status="IDLE")
                    continue
                
                except asyncio.CancelledError:
                    logger.info("🛑 Worker cancelled", 
                              worker_id=worker.worker_id,
                              worker_status="CANCELLED")
                    break
                
                except Exception as e:
                    logger.error("💥 Unexpected error in worker loop",
                               worker_id=worker.worker_id,
                               worker_status="ERROR",
                               error=str(e),
                               error_type=type(e).__name__)
        
        finally:
            worker.is_running = False
            logger.info("🔴 Worker stopped", 
                       worker_id=worker.worker_id,
                       worker_status="STOPPED",
                       final_stats=worker.get_stats())
    
    async def _process_results(self):
        """Process results from workers"""
        logger.debug("Result processor started")
        
        try:
            while self.is_running:
                try:
                    result = await asyncio.wait_for(
                        self.result_queue.get(), timeout=1.0
                    )
                    
                    # Call appropriate callback
                    if result.success and self.on_result:
                        await self.on_result(result)
                    elif not result.success and self.on_error:
                        await self.on_error(result)
                
                except asyncio.TimeoutError:
                    continue
                
                except asyncio.CancelledError:
                    break
                
                except Exception as e:
                    logger.error("Error processing result", error=str(e))
        
        finally:
            logger.debug("Result processor stopped")
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        worker_stats = [worker.get_stats() for worker in self.workers]
        
        total_processed = sum(stats['requests_processed'] for stats in worker_stats)
        total_failed = sum(stats['requests_failed'] for stats in worker_stats)
        total_retried = sum(stats['requests_retried'] for stats in worker_stats)
        
        return {
            'active_workers': len([w for w in self.workers if w.is_running]),
            'total_workers': len(self.workers),
            'queue_size': self.get_queue_size(),
            'total_processed': total_processed,
            'total_failed': total_failed,
            'total_retried': total_retried,
            'circuit_breaker_state': self.resilience.circuit_breaker.state,
            'circuit_breaker_failures': self.resilience.circuit_breaker.failure_count
        }
