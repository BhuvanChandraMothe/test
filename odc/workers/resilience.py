"""Resilience patterns for SAP OData connector workers"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import structlog
from aiolimiter import AsyncLimiter
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import Retrying, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class TokenBucketConfig:
    """Configuration for token bucket rate limiter"""
    max_rate: float = 10.0  # requests per second
    time_period: float = 1.0  # time window in seconds
    max_burst: Optional[int] = None  # max burst size


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = httpx.HTTPError


@dataclass
class RetryConfig:
    """Configuration for retry mechanism"""
    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 60.0
    multiplier: float = 2.0


class TokenBucket:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, config: TokenBucketConfig):
        self.config = config
        self.rate_limiter = AsyncLimiter(
            max_rate=config.max_rate,
            time_period=config.time_period
        )
    
    async def acquire(self) -> None:
        """Acquire a token from the bucket"""
        await self.rate_limiter.acquire()
        logger.debug("Token acquired from rate limiter")


class AsyncCircuitBreaker:
    """Async-compatible circuit breaker"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self._circuit_breaker = CircuitBreaker(
            fail_max=config.failure_threshold,
            reset_timeout=config.recovery_timeout
        )
    
    async def call(self, func: Callable[..., Awaitable], *args, **kwargs):
        """Execute function with circuit breaker protection"""
        try:
            # For async functions, we need to handle circuit breaker logic manually
            # since pybreaker doesn't natively support async
            if self._circuit_breaker.current_state == 'open':
                raise CircuitBreakerError("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                # Reset failure count on success
                self._circuit_breaker._failure_count = 0
                return result
            except Exception as e:
                # Increment failure count
                self._circuit_breaker._failure_count += 1
                if self._circuit_breaker._failure_count >= self._circuit_breaker._failure_threshold:
                    self._circuit_breaker._state = 'open'
                    self._circuit_breaker._opened = asyncio.get_event_loop().time()
                raise
                
        except CircuitBreakerError as e:
            logger.warning("Circuit breaker is open", error=str(e))
            raise
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state"""
        return self._circuit_breaker.current_state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count"""
        return self._circuit_breaker.fail_counter


class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.retryer = Retrying(
            stop=stop_after_attempt(config.max_attempts),
            wait=wait_exponential(
                multiplier=config.multiplier,
                min=config.min_wait,
                max=config.max_wait
            ),
            retry=retry_if_exception_type((
                httpx.HTTPError,
                httpx.TimeoutException,
                httpx.ConnectError
            ))
        )
    
    async def execute(self, func: Callable[..., Awaitable], *args, **kwargs):
        """Execute function with retry logic"""
        async for attempt in self.retryer:
            with attempt:
                try:
                    result = await func(*args, **kwargs)
                    if attempt.retry_state.attempt_number > 1:
                        logger.info("Retry succeeded", 
                                  attempt=attempt.retry_state.attempt_number)
                    return result
                except Exception as e:
                    logger.warning("Attempt failed", 
                                 attempt=attempt.retry_state.attempt_number,
                                 error=str(e))
                    raise


class TokenManager:
    """Singleton token manager for OAuth/JWT token refresh"""
    
    _instance: Optional['TokenManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, odata_config):
        if hasattr(self, '_initialized'):
            return
        
        self.odata_config = odata_config
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self._refresh_lock = asyncio.Lock()
        self._initialized = True
    
    async def get_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary"""
        if self._needs_refresh():
            async with self._refresh_lock:
                # Double-check after acquiring lock
                if self._needs_refresh():
                    await self._refresh_token()
        
        return self._access_token
    
    def _needs_refresh(self) -> bool:
        """Check if token needs to be refreshed"""
        if not self._access_token:
            return True
        
        if not self._token_expires_at:
            return True
        
        # Refresh 5 minutes before expiry
        return time.time() >= (self._token_expires_at - 300)
    
    async def _refresh_token(self):
        """Refresh the access token"""
        logger.info("Refreshing access token")
        
        try:
            # Implement OAuth2 token refresh logic here
            # This is a placeholder - actual implementation depends on OAuth setup
            
            if self.odata_config.client_id and self.odata_config.client_secret:
                # OAuth2 flow
                token_data = await self._oauth2_refresh()
            else:
                # Basic auth - no token refresh needed
                self._access_token = "basic_auth"
                self._token_expires_at = time.time() + 3600  # 1 hour
                return
            
            self._access_token = token_data['access_token']
            self._token_expires_at = time.time() + token_data.get('expires_in', 3600)
            
            logger.info("Access token refreshed successfully")
            
        except Exception as e:
            logger.error("Failed to refresh access token", error=str(e))
            raise
    
    async def _oauth2_refresh(self) -> Dict[str, Any]:
        """Perform OAuth2 token refresh"""
        # Placeholder for OAuth2 implementation
        # In a real implementation, this would call the SAP OAuth endpoint
        
        token_url = f"{self.odata_config.service_url}/oauth/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.odata_config.client_id,
                    'client_secret': self.odata_config.client_secret
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            return response.json()


class ConnectionPool:
    """Shared HTTP connection pool"""
    
    def __init__(self, odata_config, max_connections: int = 100):
        self.odata_config = odata_config
        self._client: Optional[httpx.AsyncClient] = None
        self.max_connections = max_connections
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self._client is None:
            limits = httpx.Limits(
                max_keepalive_connections=self.max_connections,
                max_connections=self.max_connections * 2
            )
            
            self._client = httpx.AsyncClient(
                timeout=self.odata_config.timeout,
                verify=self.odata_config.verify_ssl,
                limits=limits
            )
        
        return self._client
    
    async def close(self):
        """Close the connection pool"""
        if self._client:
            await self._client.aclose()
            self._client = None


@dataclass
class ResilienceComponents:
    """Container for all resilience components"""
    token_bucket: TokenBucket
    circuit_breaker: AsyncCircuitBreaker
    retry_handler: RetryHandler
    token_manager: TokenManager
    connection_pool: ConnectionPool
    
    @classmethod
    def create_default(cls, sap_config) -> 'ResilienceComponents':
        """Create resilience components with default configurations"""
        return cls(
            token_bucket=TokenBucket(TokenBucketConfig()),
            circuit_breaker=AsyncCircuitBreaker(CircuitBreakerConfig()),
            retry_handler=RetryHandler(RetryConfig()),
            token_manager=TokenManager(sap_config),
            connection_pool=ConnectionPool(sap_config)
        )
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.connection_pool.close()
