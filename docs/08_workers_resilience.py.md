# workers/resilience.py - Resilience Patterns Documentation

## Overview
The `workers/resilience.py` file implements resilience patterns for the SAP OData Connector, including rate limiting, circuit breakers, and retry mechanisms. These patterns protect against service failures and prevent overwhelming external systems.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
import time
from typing import Callable, Any, Awaitable, Optional
from aiolimiter import AsyncLimiter
import pybreaker
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
```

**Library Concepts:**
- **aiolimiter**: Async rate limiting using token bucket algorithm
- **pybreaker**: Circuit breaker pattern implementation
- **tenacity**: Retry logic with exponential backoff
- **asyncio**: Asynchronous programming primitives
- **structlog**: Structured logging for resilience events

### TokenBucket Rate Limiter
```python
class TokenBucket:
    """Rate limiter using token bucket algorithm"""
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket rate limiter
        
        Args:
            rate: Tokens per second (requests per second)
            capacity: Maximum tokens in bucket (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self._limiter = AsyncLimiter(max_rate=rate, time_period=1.0)
        self.logger = structlog.get_logger(__name__)
    
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens from the bucket (blocking if necessary)"""
        await self._limiter.acquire(tokens)
        self.logger.debug("Token acquired", tokens=tokens, rate=self.rate)
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking"""
        # aiolimiter doesn't have non-blocking acquire, so we simulate it
        # This is a simplified implementation
        return True  # For now, always allow (could be enhanced)
    
    @property
    def available_tokens(self) -> int:
        """Get approximate number of available tokens"""
        # This is an approximation since aiolimiter doesn't expose internal state
        return self.capacity
```

**Token Bucket Algorithm Concepts:**
- **Rate limiting**: Control request rate to external services
- **Burst capacity**: Allow short bursts above average rate
- **Token acquisition**: Block until tokens are available
- **Non-blocking check**: Try to acquire without waiting
- **Async-friendly**: Works with asyncio event loop

### AsyncCircuitBreaker Implementation
```python
class AsyncCircuitBreaker:
    """Async-compatible circuit breaker wrapper"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        # Create pybreaker circuit breaker with correct parameter names
        self._circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=failure_threshold,      # Maximum failures before opening
            reset_timeout=recovery_timeout   # Timeout before attempting reset
        )
        
        self.logger = structlog.get_logger(__name__)
    
    async def call(self, func: Callable[..., Awaitable], *args, **kwargs):
        """Execute function with circuit breaker protection"""
        try:
            # For async functions, we need to handle circuit breaker logic manually
            # since pybreaker doesn't natively support async
            if self._circuit_breaker.current_state == 'open':
                raise pybreaker.CircuitBreakerError("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                # Reset failure count on success
                self._circuit_breaker._failure_count = 0
                return result
            except Exception as e:
                # Increment failure count
                self._circuit_breaker._failure_count += 1
                if self._circuit_breaker._failure_count >= self._circuit_breaker._fail_max:
                    self._circuit_breaker._state = 'open'
                    self._circuit_breaker._opened = time.time()
                raise
            
        except pybreaker.CircuitBreakerError as e:
            self.logger.warning("Circuit breaker is open", error=str(e))
            raise
        except Exception as e:
            self.logger.error("Circuit breaker call failed", error=str(e))
            raise
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state"""
        return self._circuit_breaker.current_state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count"""
        return getattr(self._circuit_breaker, '_failure_count', 0)
    
    def reset(self) -> None:
        """Manually reset the circuit breaker"""
        self._circuit_breaker.reset()
        self.logger.info("Circuit breaker manually reset")
```

**Circuit Breaker Pattern Concepts:**
- **Failure threshold**: Number of failures before opening circuit
- **Open state**: Reject all requests when service is failing
- **Half-open state**: Allow limited requests to test service recovery
- **Closed state**: Normal operation, all requests allowed
- **Recovery timeout**: Time to wait before testing service recovery
- **Manual handling**: Custom async logic since pybreaker isn't async-native

### RetryHandler with Exponential Backoff
```python
class RetryHandler:
    """Handles retries with exponential backoff"""
    
    def __init__(
        self, 
        max_retries: int = 3, 
        backoff_factor: float = 2.0,
        max_backoff: float = 60.0
    ):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
            max_backoff: Maximum delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.logger = structlog.get_logger(__name__)
    
    async def execute(self, func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info("Retry succeeded", attempt=attempt)
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Calculate backoff delay
                    delay = min(
                        self.backoff_factor ** attempt,
                        self.max_backoff
                    )
                    
                    self.logger.warning(
                        "Retry attempt failed, backing off",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        delay=delay,
                        error=str(e)
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        "All retry attempts failed",
                        total_attempts=attempt + 1,
                        error=str(e)
                    )
        
        # All retries exhausted
        raise last_exception
    
    def should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry"""
        # Customize retry logic based on exception type
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            # Add more retryable exception types
        )
        
        return isinstance(exception, retryable_exceptions)
```

**Retry Pattern Concepts:**
- **Exponential backoff**: Increase delay between retries exponentially
- **Maximum backoff**: Cap the delay to prevent excessive waiting
- **Attempt counting**: Track retry attempts for logging and limits
- **Exception classification**: Only retry for transient errors
- **Jitter**: Could add randomness to prevent thundering herd

### Tenacity-based Retry Decorator
```python
class TenacityRetryHandler:
    """Alternative retry handler using tenacity library"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.logger = structlog.get_logger(__name__)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    async def execute_with_tenacity(self, func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        """Execute function with tenacity retry decorator"""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self.logger.warning("Tenacity retry attempt", error=str(e))
            raise
```

**Tenacity Library Features:**
- **Declarative retries**: Use decorators to define retry behavior
- **Flexible conditions**: Retry based on exception type, return value, etc.
- **Built-in strategies**: Exponential backoff, fixed delay, random jitter
- **Stop conditions**: Max attempts, max time, custom conditions
- **Async support**: Native async/await compatibility

### Resilience Pattern Composition
```python
class ResilientExecutor:
    """Combines multiple resilience patterns"""
    
    def __init__(
        self,
        rate_limiter: Optional[TokenBucket] = None,
        circuit_breaker: Optional[AsyncCircuitBreaker] = None,
        retry_handler: Optional[RetryHandler] = None
    ):
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.retry_handler = retry_handler
        self.logger = structlog.get_logger(__name__)
    
    async def execute(self, func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        """Execute function with all configured resilience patterns"""
        
        # Layer 1: Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        
        # Layer 2: Circuit breaker
        if self.circuit_breaker:
            return await self.circuit_breaker.call(
                self._execute_with_retry, func, *args, **kwargs
            )
        else:
            return await self._execute_with_retry(func, *args, **kwargs)
    
    async def _execute_with_retry(self, func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        if self.retry_handler:
            return await self.retry_handler.execute(func, *args, **kwargs)
        else:
            return await func(*args, **kwargs)
```

**Pattern Composition Concepts:**
- **Layered protection**: Multiple resilience patterns work together
- **Configurable**: Enable/disable patterns as needed
- **Order matters**: Rate limiting → Circuit breaker → Retry
- **Separation of concerns**: Each pattern handles specific failure modes

### Advanced Rate Limiting
```python
class AdaptiveRateLimiter:
    """Rate limiter that adapts based on service response"""
    
    def __init__(self, initial_rate: float = 5.0, min_rate: float = 1.0, max_rate: float = 20.0):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self._limiter = AsyncLimiter(max_rate=initial_rate, time_period=1.0)
        self._success_count = 0
        self._failure_count = 0
        self.logger = structlog.get_logger(__name__)
    
    async def acquire(self) -> None:
        """Acquire token with current rate"""
        await self._limiter.acquire()
    
    def record_success(self) -> None:
        """Record successful request"""
        self._success_count += 1
        
        # Increase rate if we have consecutive successes
        if self._success_count >= 10 and self._failure_count == 0:
            self._increase_rate()
            self._success_count = 0
    
    def record_failure(self) -> None:
        """Record failed request"""
        self._failure_count += 1
        self._success_count = 0
        
        # Decrease rate on failures
        if self._failure_count >= 3:
            self._decrease_rate()
            self._failure_count = 0
    
    def _increase_rate(self) -> None:
        """Increase rate limit"""
        old_rate = self.current_rate
        self.current_rate = min(self.current_rate * 1.5, self.max_rate)
        
        if self.current_rate != old_rate:
            self._update_limiter()
            self.logger.info("Rate limit increased", 
                           old_rate=old_rate, 
                           new_rate=self.current_rate)
    
    def _decrease_rate(self) -> None:
        """Decrease rate limit"""
        old_rate = self.current_rate
        self.current_rate = max(self.current_rate * 0.5, self.min_rate)
        
        if self.current_rate != old_rate:
            self._update_limiter()
            self.logger.info("Rate limit decreased", 
                           old_rate=old_rate, 
                           new_rate=self.current_rate)
    
    def _update_limiter(self) -> None:
        """Update internal limiter with new rate"""
        self._limiter = AsyncLimiter(max_rate=self.current_rate, time_period=1.0)
```

**Adaptive Rate Limiting Concepts:**
- **Dynamic adjustment**: Rate changes based on service response
- **Success tracking**: Increase rate when service is healthy
- **Failure response**: Decrease rate when service is struggling
- **Bounded adjustment**: Keep rate within reasonable limits
- **Hysteresis**: Different thresholds for increase vs decrease

## Advanced Resilience Concepts

### Bulkhead Pattern
```python
class BulkheadExecutor:
    """Isolate different types of operations"""
    
    def __init__(self):
        # Separate semaphores for different operation types
        self.metadata_semaphore = asyncio.Semaphore(2)    # Limited metadata ops
        self.data_semaphore = asyncio.Semaphore(10)       # More data ops allowed
        self.count_semaphore = asyncio.Semaphore(5)       # Medium count ops
    
    async def execute_metadata_operation(self, func, *args, **kwargs):
        async with self.metadata_semaphore:
            return await func(*args, **kwargs)
    
    async def execute_data_operation(self, func, *args, **kwargs):
        async with self.data_semaphore:
            return await func(*args, **kwargs)
    
    async def execute_count_operation(self, func, *args, **kwargs):
        async with self.count_semaphore:
            return await func(*args, **kwargs)
```

### Timeout Pattern
```python
class TimeoutHandler:
    """Handle operation timeouts"""
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self.logger = structlog.get_logger(__name__)
    
    async def execute_with_timeout(
        self, 
        func: Callable[..., Awaitable], 
        timeout: Optional[float] = None,
        *args, 
        **kwargs
    ) -> Any:
        """Execute function with timeout"""
        timeout = timeout or self.default_timeout
        
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error("Operation timed out", timeout=timeout)
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
```

### Health Check Pattern
```python
class HealthChecker:
    """Monitor service health"""
    
    def __init__(self, service_url: str, check_interval: float = 60.0):
        self.service_url = service_url
        self.check_interval = check_interval
        self.is_healthy = True
        self.last_check = 0
        self.logger = structlog.get_logger(__name__)
    
    async def check_health(self) -> bool:
        """Check if service is healthy"""
        now = time.time()
        
        if now - self.last_check < self.check_interval:
            return self.is_healthy
        
        try:
            # Simple health check - try to fetch metadata
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.service_url}/$metadata", timeout=10.0)
                self.is_healthy = response.status_code == 200
        except Exception as e:
            self.logger.warning("Health check failed", error=str(e))
            self.is_healthy = False
        
        self.last_check = now
        return self.is_healthy
```

## Key Programming Concepts

### 1. **Token Bucket Algorithm**
```python
class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # Tokens per second
        self.capacity = capacity  # Maximum tokens
        self.tokens = capacity    # Current tokens
        self.last_update = time.time()
    
    def acquire(self, tokens: int = 1) -> bool:
        now = time.time()
        # Add tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
```

### 2. **Circuit Breaker States**
```python
class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery

# State transitions:
# CLOSED → OPEN (on failure threshold)
# OPEN → HALF_OPEN (after timeout)
# HALF_OPEN → CLOSED (on success)
# HALF_OPEN → OPEN (on failure)
```

### 3. **Exponential Backoff**
```python
def calculate_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay"""
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)

# Example delays: 1s, 2s, 4s, 8s, 16s, 32s, 60s, 60s, ...
```

### 4. **Async Context Manager for Resources**
```python
class ResilientHttpClient:
    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def get(self, url: str) -> httpx.Response:
        # Apply all resilience patterns
        return await self.resilient_executor.execute(
            self.client.get, url
        )
```

## Usage Examples

### Basic Resilience Setup
```python
from workers.resilience import TokenBucket, AsyncCircuitBreaker, RetryHandler

# Create resilience components
rate_limiter = TokenBucket(rate=5.0, capacity=10)
circuit_breaker = AsyncCircuitBreaker(failure_threshold=3, recovery_timeout=30)
retry_handler = RetryHandler(max_retries=3, backoff_factor=2.0)

# Use in HTTP requests
async def make_resilient_request(url: str):
    await rate_limiter.acquire()
    
    return await circuit_breaker.call(
        retry_handler.execute,
        httpx.get,
        url
    )
```

### Composed Resilience Patterns
```python
executor = ResilientExecutor(
    rate_limiter=TokenBucket(rate=10.0, capacity=20),
    circuit_breaker=AsyncCircuitBreaker(failure_threshold=5),
    retry_handler=RetryHandler(max_retries=3)
)

async def fetch_data(entity_name: str):
    return await executor.execute(
        make_odata_request,
        entity_name
    )
```

### Adaptive Rate Limiting
```python
adaptive_limiter = AdaptiveRateLimiter(initial_rate=5.0)

async def make_adaptive_request(url: str):
    await adaptive_limiter.acquire()
    
    try:
        response = await httpx.get(url)
        adaptive_limiter.record_success()
        return response
    except Exception as e:
        adaptive_limiter.record_failure()
        raise
```

### Custom Resilience Pattern
```python
class CustomResilientClient:
    def __init__(self):
        self.rate_limiter = TokenBucket(rate=5.0, capacity=10)
        self.circuit_breaker = AsyncCircuitBreaker(failure_threshold=3)
        self.health_checker = HealthChecker("https://api.example.com")
    
    async def make_request(self, url: str):
        # Check service health first
        if not await self.health_checker.check_health():
            raise ServiceUnavailableError("Service is unhealthy")
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Execute with circuit breaker
        return await self.circuit_breaker.call(httpx.get, url)
```

This file demonstrates enterprise-grade resilience patterns essential for reliable distributed systems and external service integration.
