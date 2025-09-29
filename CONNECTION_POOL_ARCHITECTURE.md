# SAP OData Connector - Connection Pool & Multi-Connection Management

## 🏗️ **Architecture Overview**

The SAP OData Connector uses a sophisticated multi-layered architecture for managing connections and workers:

```
┌─────────────────────────────────────────────────────────────┐
│                    SAP OData Connector                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   ProxyPool     │    │  ResilienceComponents            │
│  │                 │    │                                  │
│  │ ┌─────────────┐ │    │ ┌─────────────┐                 │
│  │ │ProxyWorker 1│ │    │ │ConnectionPool│                 │
│  │ │ProxyWorker 2│ │◄───┤ │TokenBucket   │                 │
│  │ │ProxyWorker N│ │    │ │CircuitBreaker│                 │
│  │ └─────────────┘ │    │ │RetryHandler  │                 │
│  └─────────────────┘    │ │TokenManager  │                 │
│                         │ └─────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 **Dynamic Worker & Connection Scaling**

### **1. Dynamic Worker Calculation**
```python
def _calculate_optimal_workers(self, entity_count: int) -> int:
    # Formula: max(2, min(entity_count // 2, 10))
    base_workers = max(2, min(entity_count // 2, 10))
    
    # User preference acts as a cap, not minimum
    user_preference = self.config.max_workers  # From runtime parameters
    optimal = min(base_workers, user_preference) if user_preference > 0 else base_workers
    
    return optimal
```

**Examples:**
- **5 entities** → 2 workers (minimum enforced)
- **10 entities** → 5 workers (optimal ratio)
- **30 entities** → 10 workers (maximum cap)
- **50 entities + user_max=6** → 6 workers (user cap applied)

### **2. Dynamic Connection Pool Calculation**
```python
def _calculate_optimal_connections(self, worker_count: int) -> int:
    # Formula: max(10, min(worker_count * 4, 100))
    base_connections = worker_count * 4
    optimal = max(10, min(base_connections, 100))
    
    return optimal
```

**Reasoning for 4 connections per worker:**
- **Main request connection**
- **Retry connection** (for failed requests)
- **Concurrent batch processing**
- **Connection pool efficiency** (avoid starvation)

**Examples:**
- **2 workers** → 10 connections (minimum enforced)
- **5 workers** → 20 connections (5 × 4)
- **10 workers** → 40 connections (10 × 4)
- **30 workers** → 100 connections (maximum cap)

## 🏊 **Connection Pool Management**

### **ConnectionPool Class** (`odc/workers/resilience.py`)

```python
class ConnectionPool:
    def __init__(self, odata_config, max_connections: int = 100):
        self.max_connections = max_connections
        self._client: Optional[httpx.AsyncClient] = None
        self._is_validated = False
        self._validation_lock = asyncio.Lock()
```

#### **Key Features:**

1. **HTTP/2 Support with Fallback**
```python
# Try HTTP/2 first for better performance
self._client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=self.max_connections,
        max_connections=self.max_connections * 2,  # 2x for burst capacity
        keepalive_expiry=30.0  # Keep alive for 30 seconds
    ),
    http2=True  # Enable HTTP/2
)

# Fallback to HTTP/1.1 if HTTP/2 fails
except Exception:
    self._client = httpx.AsyncClient(http2=False)
```

2. **Connection Validation**
```python
async def validate_connection(self) -> bool:
    # Test connection with service root
    response = await client.get(self.odata_config.service_url)
    
    # Accept 200=OK, 307=Redirect, 401=Auth needed
    if response.status_code in [200, 307, 401]:
        self._is_validated = True
        return True
```

3. **Shared Connection Pool**
- **Single httpx.AsyncClient** shared across all workers
- **Connection reuse** for efficiency
- **Automatic connection management** (keep-alive, pooling)

## 👷 **Worker Pool Management**

### **ProxyPool Class** (`odc/workers/proxy_pool.py`)

```python
class ProxyPool:
    def __init__(self, worker_count: int, resilience: ResilienceComponents):
        self.workers = [
            ProxyWorker(f"worker_{i+1}", odata_config, resilience) 
            for i in range(worker_count)
        ]
        self.queue = asyncio.Queue(maxsize=1000)  # Command queue
        self.result_queue = asyncio.Queue()       # Result queue
        self.semaphore = asyncio.Semaphore(worker_count)  # Concurrency control
```

#### **Worker Lifecycle:**

1. **Worker Creation**
```python
# Each worker gets:
# - Unique worker_id (worker_1, worker_2, etc.)
# - Shared ODataConfig (credentials, URLs)
# - Shared ResilienceComponents (connection pool, rate limiter, etc.)

for i in range(worker_count):
    worker = ProxyWorker(f"worker_{i+1}", odata_config, resilience)
    self.workers.append(worker)
```

2. **Worker Loop**
```python
async def _worker_loop(self, worker: ProxyWorker):
    while self.is_running:
        # Pick up command from queue
        command = await self.queue.get()
        
        # Execute with semaphore (concurrency control)
        async with self.semaphore:
            result = await worker.execute(command)
            await self.result_queue.put(result)
            self.queue.task_done()
```

3. **Command Distribution**
```python
# Commands are distributed via asyncio.Queue
# Workers compete for commands (first-come-first-served)
await self.queue.put(command)  # Add command
command = await self.queue.get()  # Worker picks up
```

## 🛡️ **Resilience Patterns**

### **1. Rate Limiting (Token Bucket)**
```python
class TokenBucket:
    def __init__(self, max_rate: float = 10.0):
        self.limiter = AsyncLimiter(max_rate, time_period=1.0)
    
    async def acquire(self):
        await self.limiter.acquire()  # Wait for token
```

### **2. Circuit Breaker**
```python
class AsyncCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    async def call(self, func, *args, **kwargs):
        return await self._circuit_breaker(func)(*args, **kwargs)
```

### **3. Retry Handler**
```python
class RetryHandler:
    def __init__(self):
        self.retryer = Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2.0, min=1.0, max=60.0),
            retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
        )
```

### **4. Token Management (OAuth)**
```python
class TokenManager:
    async def get_valid_token(self) -> str:
        if self._is_token_expired():
            await self._refresh_token()
        return self._access_token
    
    async def _refresh_token(self):
        # OAuth2 token refresh logic
        token_data = await self._oauth2_refresh()
        self._access_token = token_data['access_token']
```

## 📊 **Connection Flow Example**

### **Scenario: 15 Entities, 5 Workers, 20 Connections**

```
1. Initialization:
   ├── Calculate workers: max(2, min(15//2, 10)) = 7 → capped to 5 (user preference)
   ├── Calculate connections: max(10, min(5*4, 100)) = 20
   └── Create connection pool with 20 max connections

2. Worker Creation:
   ├── worker_1 ┐
   ├── worker_2 ├── All share the same ConnectionPool (20 connections)
   ├── worker_3 ├── All share the same ResilienceComponents
   ├── worker_4 ├── Each has unique worker_id for tracking
   └── worker_5 ┘

3. Command Execution:
   ├── Commands added to asyncio.Queue
   ├── Workers compete for commands (FIFO)
   ├── Each worker uses shared connection pool
   └── Rate limiting applied across all workers

4. Connection Usage:
   ├── httpx.AsyncClient manages 20 connections
   ├── HTTP/2 multiplexing (multiple requests per connection)
   ├── Keep-alive connections (30 second expiry)
   └── Automatic connection recycling
```

## 🔍 **Monitoring & Statistics**

### **Pool Statistics**
```python
def get_pool_stats(self) -> Dict[str, Any]:
    return {
        'active_workers': len([w for w in self.workers if w.is_running]),
        'total_workers': len(self.workers),
        'queue_size': self.queue.qsize(),
        'total_processed': sum(worker.requests_processed),
        'total_failed': sum(worker.requests_failed),
        'circuit_breaker_state': self.resilience.circuit_breaker.state,
        'connection_pool_status': await self.resilience.connection_pool.get_pool_stats()
    }
```

### **Connection Pool Statistics**
```python
async def get_pool_stats(self) -> Dict[str, Any]:
    return {
        "status": "active",
        "is_validated": self._is_validated,
        "max_connections": self.max_connections,
        "client_closed": self._client.is_closed
    }
```

## ⚡ **Performance Optimizations**

### **1. Connection Reuse**
- **Keep-alive connections** (30 seconds)
- **HTTP/2 multiplexing** (multiple requests per connection)
- **Connection pooling** (shared across workers)

### **2. Concurrency Control**
- **Semaphore** limits concurrent workers
- **Rate limiting** prevents server overload
- **Circuit breaker** prevents cascade failures

### **3. Efficient Resource Management**
- **Shared connection pool** (not per-worker)
- **Dynamic scaling** based on workload
- **Automatic cleanup** on shutdown

## 🎯 **Key Benefits**

### ✅ **Scalability**
- Dynamic worker scaling (2-10 workers)
- Dynamic connection scaling (10-100 connections)
- Efficient resource utilization

### ✅ **Reliability**
- Circuit breaker prevents cascade failures
- Retry logic handles transient errors
- Connection validation ensures health

### ✅ **Performance**
- HTTP/2 support for better throughput
- Connection pooling reduces overhead
- Rate limiting prevents server overload

### ✅ **Monitoring**
- Detailed statistics and metrics
- Real-time pool status
- Worker performance tracking

---

**Summary**: The SAP OData Connector uses a sophisticated multi-layered architecture with dynamic scaling, shared connection pooling, and comprehensive resilience patterns to efficiently handle concurrent SAP data extraction while maintaining reliability and performance! 🚀
