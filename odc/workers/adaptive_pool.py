"""
Adaptive Connection Pool with Health Monitoring and Auto-scaling
"""

import asyncio
import httpx
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import structlog
from datetime import datetime, timezone, timedelta
import statistics
import weakref

logger = structlog.get_logger(__name__)


class PoolState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"


class ConnectionState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    FAILED = "failed"
    QUARANTINED = "quarantined"


@dataclass
class ConnectionMetrics:
    """Metrics for individual connections"""
    connection_id: str
    created_at: datetime
    state: ConnectionState = ConnectionState.IDLE
    requests_made: int = 0
    requests_failed: int = 0
    response_times: List[float] = field(default_factory=list)
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    quarantine_until: Optional[datetime] = None
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.requests_made == 0:
            return 1.0
        return (self.requests_made - self.requests_failed) / self.requests_made
    
    @property
    def health_score(self) -> float:
        """Calculate overall health score (0.0 to 1.0)"""
        if self.state == ConnectionState.FAILED:
            return 0.0
        if self.state == ConnectionState.QUARANTINED:
            return 0.1
        
        # Base score on success rate and response time
        success_weight = 0.7
        performance_weight = 0.3
        
        success_score = self.success_rate
        
        # Performance score (lower response time = higher score)
        if self.avg_response_time == 0:
            performance_score = 1.0
        else:
            # Normalize response time (assume 1 second is baseline)
            performance_score = max(0.0, 1.0 - (self.avg_response_time - 1.0) / 2.0)
        
        return (success_score * success_weight) + (performance_score * performance_weight)
    
    def is_quarantined(self) -> bool:
        """Check if connection is quarantined"""
        if self.quarantine_until is None:
            return False
        return datetime.now(timezone.utc) < self.quarantine_until


@dataclass
class PoolMetrics:
    """Metrics for the entire connection pool"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    quarantined_connections: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_pool_response_time: float = 0.0
    pool_success_rate: float = 1.0
    last_scale_event: Optional[datetime] = None
    scale_events_count: int = 0


class AdaptiveConnectionPool:
    """Adaptive HTTP connection pool with health monitoring and auto-scaling"""
    
    def __init__(
        self,
        base_url: str,
        min_connections: int = 5,
        max_connections: int = 50,
        initial_connections: int = 10,
        scale_threshold_high: float = 0.8,  # Scale up when utilization > 80%
        scale_threshold_low: float = 0.3,   # Scale down when utilization < 30%
        health_check_interval: float = 30.0,
        quarantine_duration: float = 300.0,  # 5 minutes
        max_response_time: float = 10.0,
        max_consecutive_failures: int = 3,
        **httpx_kwargs
    ):
        self.base_url = base_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.initial_connections = initial_connections
        self.scale_threshold_high = scale_threshold_high
        self.scale_threshold_low = scale_threshold_low
        self.health_check_interval = health_check_interval
        self.quarantine_duration = quarantine_duration
        self.max_response_time = max_response_time
        self.max_consecutive_failures = max_consecutive_failures
        
        # Connection management
        self.connections: Dict[str, httpx.AsyncClient] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.connection_semaphore: Optional[asyncio.Semaphore] = None
        self.pool_metrics = PoolMetrics()
        
        # State management
        self.is_running = False
        self.pool_state = PoolState.HEALTHY
        self.last_health_check = datetime.now(timezone.utc)
        
        # Background tasks
        self.health_check_task: Optional[asyncio.Task] = None
        self.auto_scale_task: Optional[asyncio.Task] = None
        
        # HTTP client configuration
        self.httpx_kwargs = {
            'timeout': httpx.Timeout(30.0),
            'limits': httpx.Limits(max_connections=max_connections),
            'http2': True,
            **httpx_kwargs
        }
        
        # Callbacks
        self.on_scale_event: Optional[Callable[[str, int, int], None]] = None
        self.on_connection_failed: Optional[Callable[[str, str], None]] = None
        self.on_pool_state_changed: Optional[Callable[[PoolState, PoolState], None]] = None
    
    async def start(self):
        """Start the connection pool"""
        if self.is_running:
            return
        
        logger.info("Starting adaptive connection pool",
                   min_connections=self.min_connections,
                   max_connections=self.max_connections,
                   initial_connections=self.initial_connections)
        
        self.is_running = True
        self.connection_semaphore = asyncio.Semaphore(self.max_connections)
        
        # Create initial connections
        await self._create_initial_connections()
        
        # Start background tasks
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self.auto_scale_task = asyncio.create_task(self._auto_scale_loop())
        
        logger.info("Adaptive connection pool started",
                   active_connections=len(self.connections))
    
    async def stop(self):
        """Stop the connection pool"""
        if not self.is_running:
            return
        
        logger.info("Stopping adaptive connection pool")
        self.is_running = False
        
        # Cancel background tasks
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.auto_scale_task:
            self.auto_scale_task.cancel()
            try:
                await self.auto_scale_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        await self._close_all_connections()
        
        logger.info("Adaptive connection pool stopped")
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request using pool"""
        if not self.is_running:
            raise RuntimeError("Connection pool is not running")
        
        # Get available connection
        connection_id, client = await self._get_connection()
        
        try:
            # Record request start time
            start_time = time.time()
            
            # Make request
            response = await client.request(method, url, **kwargs)
            
            # Record successful request
            response_time = time.time() - start_time
            await self._record_request_success(connection_id, response_time)
            
            return response
            
        except Exception as e:
            # Record failed request
            response_time = time.time() - start_time
            await self._record_request_failure(connection_id, str(e), response_time)
            raise
        
        finally:
            # Return connection to pool
            await self._return_connection(connection_id)
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request"""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request"""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """PUT request"""
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """DELETE request"""
        return await self.request("DELETE", url, **kwargs)
    
    async def _create_initial_connections(self):
        """Create initial set of connections"""
        for i in range(self.initial_connections):
            await self._create_connection(f"conn_{i}")
    
    async def _create_connection(self, connection_id: str) -> str:
        """Create a new connection"""
        try:
            client = httpx.AsyncClient(**self.httpx_kwargs)
            self.connections[connection_id] = client
            
            # Initialize metrics
            self.connection_metrics[connection_id] = ConnectionMetrics(
                connection_id=connection_id,
                created_at=datetime.now(timezone.utc)
            )
            
            logger.debug("Connection created", connection_id=connection_id)
            return connection_id
            
        except Exception as e:
            logger.error("Failed to create connection", 
                        connection_id=connection_id, 
                        error=str(e))
            raise
    
    async def _get_connection(self) -> tuple[str, httpx.AsyncClient]:
        """Get an available connection from the pool"""
        await self.connection_semaphore.acquire()
        
        # Find best available connection
        available_connections = [
            (conn_id, metrics) for conn_id, metrics in self.connection_metrics.items()
            if (metrics.state == ConnectionState.IDLE and 
                not metrics.is_quarantined() and
                conn_id in self.connections)
        ]
        
        if not available_connections:
            # Try to create new connection if under limit
            if len(self.connections) < self.max_connections:
                conn_id = f"conn_{len(self.connections)}"
                await self._create_connection(conn_id)
                available_connections = [(conn_id, self.connection_metrics[conn_id])]
            else:
                # Wait for connection to become available
                self.connection_semaphore.release()
                await asyncio.sleep(0.1)
                return await self._get_connection()
        
        # Select connection with highest health score
        best_conn_id, best_metrics = max(available_connections, 
                                        key=lambda x: x[1].health_score)
        
        # Mark connection as active
        best_metrics.state = ConnectionState.ACTIVE
        best_metrics.last_used = datetime.now(timezone.utc)
        
        return best_conn_id, self.connections[best_conn_id]
    
    async def _return_connection(self, connection_id: str):
        """Return connection to pool"""
        if connection_id in self.connection_metrics:
            self.connection_metrics[connection_id].state = ConnectionState.IDLE
        
        self.connection_semaphore.release()
    
    async def _record_request_success(self, connection_id: str, response_time: float):
        """Record successful request"""
        if connection_id not in self.connection_metrics:
            return
        
        metrics = self.connection_metrics[connection_id]
        metrics.requests_made += 1
        metrics.response_times.append(response_time)
        metrics.consecutive_failures = 0
        
        # Keep only recent response times (last 100)
        if len(metrics.response_times) > 100:
            metrics.response_times = metrics.response_times[-100:]
        
        # Update pool metrics
        self.pool_metrics.total_requests += 1
        
        logger.debug("Request success recorded",
                    connection_id=connection_id,
                    response_time=response_time)
    
    async def _record_request_failure(self, connection_id: str, error: str, response_time: float):
        """Record failed request"""
        if connection_id not in self.connection_metrics:
            return
        
        metrics = self.connection_metrics[connection_id]
        metrics.requests_made += 1
        metrics.requests_failed += 1
        metrics.consecutive_failures += 1
        metrics.last_error = error
        metrics.response_times.append(response_time)
        
        # Update pool metrics
        self.pool_metrics.total_requests += 1
        self.pool_metrics.total_failures += 1
        
        # Check if connection should be quarantined
        if (metrics.consecutive_failures >= self.max_consecutive_failures or
            response_time > self.max_response_time):
            await self._quarantine_connection(connection_id)
        
        # Notify callback
        if self.on_connection_failed:
            try:
                self.on_connection_failed(connection_id, error)
            except Exception as e:
                logger.warning("Connection failure callback failed", error=str(e))
        
        logger.warning("Request failure recorded",
                      connection_id=connection_id,
                      error=error,
                      consecutive_failures=metrics.consecutive_failures)
    
    async def _quarantine_connection(self, connection_id: str):
        """Quarantine a problematic connection"""
        if connection_id not in self.connection_metrics:
            return
        
        metrics = self.connection_metrics[connection_id]
        metrics.state = ConnectionState.QUARANTINED
        metrics.quarantine_until = datetime.now(timezone.utc) + timedelta(seconds=self.quarantine_duration)
        
        logger.warning("Connection quarantined",
                      connection_id=connection_id,
                      quarantine_duration=self.quarantine_duration)
        
        # Close and recreate the connection
        if connection_id in self.connections:
            await self.connections[connection_id].aclose()
            del self.connections[connection_id]
        
        # Create replacement connection if needed
        if len(self.connections) < self.min_connections:
            new_conn_id = f"conn_{int(time.time())}"
            await self._create_connection(new_conn_id)
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while self.is_running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check failed", error=str(e))
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_check(self):
        """Perform health check on all connections"""
        logger.debug("Performing pool health check")
        
        current_time = datetime.now(timezone.utc)
        healthy_connections = 0
        total_connections = len(self.connection_metrics)
        
        # Check each connection
        for conn_id, metrics in list(self.connection_metrics.items()):
            # Remove quarantined connections that have expired
            if metrics.is_quarantined() and current_time >= metrics.quarantine_until:
                metrics.state = ConnectionState.IDLE
                metrics.quarantine_until = None
                metrics.consecutive_failures = 0
                logger.info("Connection released from quarantine", connection_id=conn_id)
            
            # Count healthy connections
            if metrics.health_score > 0.7:
                healthy_connections += 1
        
        # Update pool state
        old_state = self.pool_state
        
        if total_connections == 0:
            self.pool_state = PoolState.CRITICAL
        elif healthy_connections / total_connections >= 0.8:
            self.pool_state = PoolState.HEALTHY
        elif healthy_connections / total_connections >= 0.5:
            self.pool_state = PoolState.DEGRADED
        else:
            self.pool_state = PoolState.CRITICAL
        
        # Notify state change
        if old_state != self.pool_state:
            logger.info("Pool state changed",
                       old_state=old_state.value,
                       new_state=self.pool_state.value,
                       healthy_connections=healthy_connections,
                       total_connections=total_connections)
            
            if self.on_pool_state_changed:
                try:
                    self.on_pool_state_changed(old_state, self.pool_state)
                except Exception as e:
                    logger.warning("Pool state change callback failed", error=str(e))
        
        self.last_health_check = current_time
    
    async def _auto_scale_loop(self):
        """Background auto-scaling loop"""
        while self.is_running:
            try:
                await self._check_scaling_needs()
                await asyncio.sleep(60.0)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Auto-scaling check failed", error=str(e))
                await asyncio.sleep(60.0)
    
    async def _check_scaling_needs(self):
        """Check if pool needs to scale up or down"""
        if not self.connections:
            return
        
        # Calculate utilization
        active_count = sum(1 for m in self.connection_metrics.values() 
                          if m.state == ConnectionState.ACTIVE)
        total_count = len(self.connections)
        utilization = active_count / total_count if total_count > 0 else 0
        
        logger.debug("Checking scaling needs",
                    active_connections=active_count,
                    total_connections=total_count,
                    utilization=utilization)
        
        # Scale up if utilization is high
        if (utilization > self.scale_threshold_high and 
            total_count < self.max_connections):
            
            scale_count = min(5, self.max_connections - total_count)
            await self._scale_up(scale_count)
        
        # Scale down if utilization is low
        elif (utilization < self.scale_threshold_low and 
              total_count > self.min_connections):
            
            scale_count = min(5, total_count - self.min_connections)
            await self._scale_down(scale_count)
    
    async def _scale_up(self, count: int):
        """Scale up the connection pool"""
        logger.info("Scaling up connection pool", scale_count=count)
        
        for i in range(count):
            conn_id = f"conn_{int(time.time())}_{i}"
            await self._create_connection(conn_id)
        
        self.pool_metrics.last_scale_event = datetime.now(timezone.utc)
        self.pool_metrics.scale_events_count += 1
        
        if self.on_scale_event:
            try:
                self.on_scale_event("scale_up", count, len(self.connections))
            except Exception as e:
                logger.warning("Scale event callback failed", error=str(e))
    
    async def _scale_down(self, count: int):
        """Scale down the connection pool"""
        logger.info("Scaling down connection pool", scale_count=count)
        
        # Find least healthy idle connections to remove
        idle_connections = [
            (conn_id, metrics) for conn_id, metrics in self.connection_metrics.items()
            if metrics.state == ConnectionState.IDLE
        ]
        
        # Sort by health score (lowest first)
        idle_connections.sort(key=lambda x: x[1].health_score)
        
        removed_count = 0
        for conn_id, _ in idle_connections[:count]:
            await self._remove_connection(conn_id)
            removed_count += 1
        
        self.pool_metrics.last_scale_event = datetime.now(timezone.utc)
        self.pool_metrics.scale_events_count += 1
        
        if self.on_scale_event:
            try:
                self.on_scale_event("scale_down", removed_count, len(self.connections))
            except Exception as e:
                logger.warning("Scale event callback failed", error=str(e))
    
    async def _remove_connection(self, connection_id: str):
        """Remove a connection from the pool"""
        if connection_id in self.connections:
            await self.connections[connection_id].aclose()
            del self.connections[connection_id]
        
        if connection_id in self.connection_metrics:
            del self.connection_metrics[connection_id]
        
        logger.debug("Connection removed", connection_id=connection_id)
    
    async def _close_all_connections(self):
        """Close all connections"""
        for conn_id, client in list(self.connections.items()):
            try:
                await client.aclose()
            except Exception as e:
                logger.warning("Error closing connection", 
                              connection_id=conn_id, 
                              error=str(e))
        
        self.connections.clear()
        self.connection_metrics.clear()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status"""
        active_count = sum(1 for m in self.connection_metrics.values() 
                          if m.state == ConnectionState.ACTIVE)
        idle_count = sum(1 for m in self.connection_metrics.values() 
                        if m.state == ConnectionState.IDLE)
        failed_count = sum(1 for m in self.connection_metrics.values() 
                          if m.state == ConnectionState.FAILED)
        quarantined_count = sum(1 for m in self.connection_metrics.values() 
                               if m.state == ConnectionState.QUARANTINED)
        
        # Calculate overall pool health
        if self.connection_metrics:
            avg_health = statistics.mean([m.health_score for m in self.connection_metrics.values()])
            avg_response_time = statistics.mean([m.avg_response_time for m in self.connection_metrics.values() if m.response_times])
        else:
            avg_health = 0.0
            avg_response_time = 0.0
        
        return {
            'state': self.pool_state.value,
            'is_running': self.is_running,
            'total_connections': len(self.connections),
            'active_connections': active_count,
            'idle_connections': idle_count,
            'failed_connections': failed_count,
            'quarantined_connections': quarantined_count,
            'utilization': active_count / len(self.connections) if self.connections else 0,
            'avg_health_score': avg_health,
            'avg_response_time': avg_response_time,
            'total_requests': self.pool_metrics.total_requests,
            'total_failures': self.pool_metrics.total_failures,
            'success_rate': ((self.pool_metrics.total_requests - self.pool_metrics.total_failures) / 
                           self.pool_metrics.total_requests) if self.pool_metrics.total_requests > 0 else 1.0,
            'last_health_check': self.last_health_check.isoformat(),
            'last_scale_event': self.pool_metrics.last_scale_event.isoformat() if self.pool_metrics.last_scale_event else None,
            'scale_events_count': self.pool_metrics.scale_events_count
        }
    
    def get_connection_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about all connections"""
        return [
            {
                'connection_id': conn_id,
                'state': metrics.state.value,
                'created_at': metrics.created_at.isoformat(),
                'requests_made': metrics.requests_made,
                'requests_failed': metrics.requests_failed,
                'success_rate': metrics.success_rate,
                'avg_response_time': metrics.avg_response_time,
                'health_score': metrics.health_score,
                'consecutive_failures': metrics.consecutive_failures,
                'last_used': metrics.last_used.isoformat() if metrics.last_used else None,
                'last_error': metrics.last_error,
                'is_quarantined': metrics.is_quarantined(),
                'quarantine_until': metrics.quarantine_until.isoformat() if metrics.quarantine_until else None
            }
            for conn_id, metrics in self.connection_metrics.items()
        ]
