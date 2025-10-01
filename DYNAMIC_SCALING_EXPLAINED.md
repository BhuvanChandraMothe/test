# Dynamic Scaling in SAP OData Connector

## 🎯 Overview

The SAP OData Connector now automatically calculates optimal `max_workers` and `max_connections` based on your workload, eliminating the need for manual configuration.

##  How Dynamic Worker Calculation Works

### Formula: `max(2, min(entity_count // 2, 10))`

**Logic:**
1. **Base calculation**: 1 worker per 2-3 entities (`entity_count // 2`)
2. **Minimum**: 2 workers (ensures parallelism even for small datasets)
3. **Maximum**: 10 workers (prevents resource exhaustion)
4. **User preference**: Acts as a cap, not a minimum

### Examples:

| Entities | Calculation | Workers | Reasoning |
|----------|-------------|---------|-----------|
| 3 entities | `max(2, min(3//2, 10))` = `max(2, min(1, 10))` = **2** | 2 workers | Minimum enforced |
| 5 entities | `max(2, min(5//2, 10))` = `max(2, min(2, 10))` = **2** | 2 workers | Balanced |
| 10 entities | `max(2, min(10//2, 10))` = `max(2, min(5, 10))` = **5** | 5 workers | Optimal |
| 20 entities | `max(2, min(20//2, 10))` = `max(2, min(10, 10))` = **10** | 10 workers | Maximum reached |
| 50 entities | `max(2, min(50//2, 10))` = `max(2, min(25, 10))` = **10** | 10 workers | Capped at maximum |

### User Preference as Cap:
```python
config = ClientConfig(max_workers=3)  # User sets maximum cap
# If calculation suggests 5 workers, it will use 3 (user's cap)
# If calculation suggests 2 workers, it will use 2 (calculation is lower)
```

##  How Dynamic Connection Pool Calculation Works

### Formula: `max(10, min(worker_count * 4, 100))`

**Logic:**
1. **Base calculation**: 4 connections per worker (`worker_count * 4`)
2. **Reasoning**: Each worker needs multiple connections for:
   - Main data request
   - Retry requests during failures
   - Concurrent batch processing
   - HTTP connection pool efficiency
3. **Minimum**: 10 connections (baseline for any workload)
4. **Maximum**: 100 connections (prevents overwhelming the server)

### Examples:

| Workers | Calculation | Connections | Ratio | Reasoning |
|---------|-------------|-------------|-------|-----------|
| 2 workers | `max(10, min(2*4, 100))` = `max(10, 8)` = **10** | 10 connections | 5.0 per worker | Minimum enforced |
| 3 workers | `max(10, min(3*4, 100))` = `max(10, 12)` = **12** | 12 connections | 4.0 per worker | Optimal |
| 5 workers | `max(10, min(5*4, 100))` = `max(10, 20)` = **20** | 20 connections | 4.0 per worker | Optimal |
| 10 workers | `max(10, min(10*4, 100))` = `max(10, 40)` = **40** | 40 connections | 4.0 per worker | Optimal |
| 25 workers | `max(10, min(25*4, 100))` = `max(10, 100)` = **100** | 100 connections | 4.0 per worker | Maximum reached |

## 📊 Real-World Scenarios

### Scenario 1: Small Dataset (5 entities)
```
Entities: 5
├── Workers: max(2, min(5//2, 10)) = 2 workers
└── Connections: max(10, min(2*4, 100)) = 10 connections
Result: 2 workers, 10 connections (5 connections per worker)
```

### Scenario 2: Medium Dataset (15 entities)
```
Entities: 15
├── Workers: max(2, min(15//2, 10)) = 7 workers
└── Connections: max(10, min(7*4, 100)) = 28 connections
Result: 7 workers, 28 connections (4 connections per worker)
```

### Scenario 3: Large Dataset (40 entities)
```
Entities: 40
├── Workers: max(2, min(40//2, 10)) = 10 workers (capped)
└── Connections: max(10, min(10*4, 100)) = 40 connections
Result: 10 workers, 40 connections (4 connections per worker)
```

### Scenario 4: With User Cap (20 entities, user sets max_workers=6)
```
Entities: 20
├── Calculated Workers: max(2, min(20//2, 10)) = 10 workers
├── User Cap: 6 workers
├── Final Workers: min(10, 6) = 6 workers
└── Connections: max(10, min(6*4, 100)) = 24 connections
Result: 6 workers, 24 connections (4 connections per worker)
```

##  Benefits of Dynamic Scaling

###  **Automatic Optimization**
- No manual tuning required
- Adapts to your specific workload
- Prevents under-utilization and over-provisioning

###  **Resource Efficiency**
- Small datasets don't waste resources
- Large datasets get appropriate parallelism
- Connection pools sized for actual needs

###  **Performance**
- Optimal worker-to-entity ratio
- Sufficient connections for concurrent requests
- Prevents connection starvation

###  **Reliability**
- Bounded limits prevent resource exhaustion
- User caps provide safety controls
- Graceful scaling for any dataset size

##  Configuration Changes

### Before (Manual Configuration):
```python
config = ClientConfig(
    max_workers=5,        # Had to guess
    max_connections=50,   # Had to guess
    # ... other settings
)
```

### After (Automatic Configuration):
```python
config = ClientConfig(
    max_workers=5,        # Optional: acts as maximum cap only
    # max_connections removed - calculated automatically
    # ... other settings
)
```

## 📈 Monitoring Dynamic Scaling

The connector logs detailed information about the scaling decisions:

```
 Dynamic Worker Calculation
   entity_count: 15
   formula: "max(2, min(entity_count // 2, 10))"
   base_calculation: 7
   user_max_preference: 5
   final_optimal: 5
   reasoning: "For 15 entities: 15//2=7, capped by user preference"

 Dynamic Connection Pool Calculation
   worker_count: 5
   formula: "max(10, min(worker_count * 4, 100))"
   base_calculation: 20
   final_optimal: 20
   reasoning: "For 5 workers: 5*4=20, bounded 10-100"
   connection_per_worker_ratio: "4.0 connections per worker"
```

## 🎯 Best Practices

1. **Let it auto-scale**: Don't set `max_workers` unless you have specific constraints
2. **Use max_workers as a safety cap**: Set it to prevent resource exhaustion on your system
3. **Monitor the logs**: Check the scaling decisions during initialization
4. **Trust the algorithm**: It's designed based on real-world performance testing

## 🔮 Why These Numbers?

### Workers: 1 worker per 2-3 entities
- **Too few workers**: Underutilizes parallelism, slower execution
- **Too many workers**: Context switching overhead, resource contention
- **Sweet spot**: 2-3 entities per worker balances parallelism with efficiency

### Connections: 4 connections per worker
- **HTTP connection reuse**: Reduces latency and overhead
- **Retry handling**: Extra connections for failed request retries
- **Batch processing**: Multiple concurrent requests per worker
- **Pool efficiency**: Prevents connection starvation

The dynamic scaling ensures your connector runs optimally regardless of dataset size! 
