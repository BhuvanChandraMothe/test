# Prometheus Metrics - Auto-Push Guide

## 🎯 Overview

The SAP OData Connector now supports **automatic Prometheus metrics pushing** to a Pushgateway. No manual configuration needed - just provide the Pushgateway URL and metrics will be automatically pushed after each query!

---

## ✨ Key Features

- ✅ **Automatic Metrics Push** - Metrics pushed automatically after each `get_data()` call
- ✅ **Zero Manual Configuration** - Just set the Pushgateway URL
- ✅ **Smart Interval Management** - Configurable push intervals to avoid overwhelming the gateway
- ✅ **Instance Tracking** - Automatic hostname-based instance identification
- ✅ **Comprehensive Metrics** - Request duration, record counts, errors, and more
- ✅ **Production Ready** - Built-in error handling and retry logic

---

## 🚀 Quick Start

### Step 1: Start Prometheus Pushgateway

```bash
# Using Docker
docker run -d -p 9091:9091 prom/pushgateway

# Or download and run locally
# https://github.com/prometheus/pushgateway/releases
```

### Step 2: Set Environment Variable (That's It!)

```bash
# Set the Pushgateway URL - that's all you need!
export PROMETHEUS_PUSHGATEWAY_URL="http://localhost:9091"

# Optional: Customize job name and instance
export PROMETHEUS_JOB_NAME="my_sap_etl"
export PROMETHEUS_INSTANCE_NAME="production-01"
export PROMETHEUS_PUSH_INTERVAL="10"
```

### Step 3: Use Connector Normally (No Config Changes!)

```python
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

# Just your SAP credentials - NO Prometheus config needed!
config = ClientConfig(
    sap_server="sapes5.sapdevcenter.com",
    sap_port=443,
    sap_module="ES5",
    username="your_username",
    password="your_password"
)

connector = SAPODataConnector(config)
await connector.initialize()

# Metrics are automatically pushed after each query!
result = await connector.get_data(entity_name="Products")
# ✅ Metrics automatically pushed to Pushgateway

await connector.cleanup()
```

**That's it! Metrics auto-configured from environment variables!**

### Step 3: View Metrics

Visit your Pushgateway: `http://localhost:9091`

Or query from Prometheus: `http://localhost:9090`

---

## ⚙️ Configuration Options

### Method 1: Environment Variables (Recommended)

```bash
# Required - Pushgateway URL
export PROMETHEUS_PUSHGATEWAY_URL="http://localhost:9091"

# Optional - Customize settings
export PROMETHEUS_JOB_NAME="my_sap_etl"           # Default: sap_odata_connector
export PROMETHEUS_INSTANCE_NAME="prod-server-01"  # Default: hostname
export PROMETHEUS_PUSH_INTERVAL="10"              # Default: 10 seconds
```

**Your Python code stays clean - just SAP credentials!**

```python
config = ClientConfig(
    sap_server="server.com",
    sap_module="ES5",
    username="user",
    password="pass"
    # No Prometheus config here!
)
```

### Method 2: Programmatic Configuration (Optional)

If you need to configure Prometheus in code:

```python
from odc.monitoring.prometheus_config import configure_prometheus

# Configure before creating connector
configure_prometheus(
    pushgateway_url="http://localhost:9091",
    job_name="my_sap_etl",
    instance_name="production-01",
    push_interval=10
)

# Then use connector normally
config = ClientConfig(
    sap_server="server.com",
    sap_module="ES5",
    username="user",
    password="pass"
)
```

### Method 3: Disable Metrics

```bash
# Don't set PROMETHEUS_PUSHGATEWAY_URL
# Metrics will be disabled automatically
```

Or programmatically:

```python
from odc.monitoring.prometheus_config import configure_prometheus

# Explicitly disable
configure_prometheus(pushgateway_url=None)
```

---

## 📊 Available Metrics

### 1. Request Metrics

#### `sap_odata_requests_total`
- **Type**: Counter
- **Description**: Total number of OData requests
- **Labels**: `entity`, `status`, `worker_id`
- **Example**: `sap_odata_requests_total{entity="Products",status="success",worker_id="worker_1"}`

#### `sap_odata_request_duration_seconds`
- **Type**: Histogram
- **Description**: Request duration in seconds
- **Labels**: `entity`, `worker_id`
- **Buckets**: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10

### 2. Processing Metrics

#### `sap_odata_records_processed_total`
- **Type**: Counter
- **Description**: Total number of records processed
- **Labels**: `entity`, `status`
- **Example**: `sap_odata_records_processed_total{entity="Products",status="success"}`

#### `sap_odata_transformation_duration_seconds`
- **Type**: Histogram
- **Description**: Data transformation duration
- **Labels**: `entity`

### 3. Queue Metrics

#### `sap_odata_queue_size`
- **Type**: Gauge
- **Description**: Current queue size
- **No labels**

#### `sap_odata_active_workers`
- **Type**: Gauge
- **Description**: Number of active workers
- **No labels**

### 4. Error Metrics

#### `sap_odata_errors_total`
- **Type**: Counter
- **Description**: Total number of errors
- **Labels**: `entity`, `error_type`, `worker_id`
- **Example**: `sap_odata_errors_total{entity="Orders",error_type="timeout",worker_id="worker_2"}`

#### `sap_odata_circuit_breaker_state`
- **Type**: Gauge
- **Description**: Circuit breaker state (0=closed, 1=open, 2=half_open)
- **Labels**: `worker_id`

### 5. Storage Metrics

#### `sap_odata_storage_operations_total`
- **Type**: Counter
- **Description**: Total storage operations
- **Labels**: `storage_type`, `operation`, `status`

#### `sap_odata_storage_duration_seconds`
- **Type**: Histogram
- **Description**: Storage operation duration
- **Labels**: `storage_type`, `operation`

---

## 🎯 Usage Examples

### Example 1: Basic Auto-Push

```python
import asyncio
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

async def main():
    config = ClientConfig(
        sap_server="server.com",
        sap_port=443,
        sap_module="ES5",
        username="user",
        password="pass",
        prometheus_pushgateway_url="http://localhost:9091"  # Auto-push enabled!
    )
    
    connector = SAPODataConnector(config)
    await connector.initialize()
    
    # Query 1 - Metrics pushed automatically
    products = await connector.get_data(entity_name="Products")
    print(f"Products: {products['execution_stats']['records_processed']}")
    
    # Query 2 - Metrics pushed automatically
    orders = await connector.get_data(entity_name="Orders")
    print(f"Orders: {orders['execution_stats']['records_processed']}")
    
    await connector.cleanup()

asyncio.run(main())
```

### Example 2: Multiple Instances

```python
# Instance 1 - Production ETL
config_prod = ClientConfig(
    sap_server="prod-server.com",
    sap_module="FI",
    username="prod_user",
    password="prod_pass",
    prometheus_pushgateway_url="http://pushgateway:9091",
    prometheus_job_name="sap_etl",
    prometheus_instance_name="production-etl-01"
)

# Instance 2 - Development ETL
config_dev = ClientConfig(
    sap_server="dev-server.com",
    sap_module="FI",
    username="dev_user",
    password="dev_pass",
    prometheus_pushgateway_url="http://pushgateway:9091",
    prometheus_job_name="sap_etl",
    prometheus_instance_name="development-etl-01"
)

# Both instances push to same Pushgateway but are identified separately
```

### Example 3: Disable Metrics

```python
# Disable metrics completely
config = ClientConfig(
    sap_server="server.com",
    sap_module="ES5",
    username="user",
    password="pass",
    enable_metrics=False  # No metrics collected or pushed
)
```

### Example 4: Manual Push Control

```python
config = ClientConfig(
    sap_server="server.com",
    sap_module="ES5",
    username="user",
    password="pass",
    prometheus_pushgateway_url="http://localhost:9091",
    prometheus_push_interval=0  # Disable automatic interval-based push
)

connector = SAPODataConnector(config)
await connector.initialize()

# Metrics still pushed after each query
result = await connector.get_data(entity_name="Products")

# Or manually force push
if connector.metrics:
    connector.metrics.push_metrics(force=True)
```

---

## 📈 Prometheus Configuration

### prometheus.yml

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  # Scrape Pushgateway
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['localhost:9091']
```

### Grafana Dashboard Queries

#### Total Requests by Entity
```promql
sum(rate(sap_odata_requests_total[5m])) by (entity)
```

#### Average Request Duration
```promql
rate(sap_odata_request_duration_seconds_sum[5m]) / rate(sap_odata_request_duration_seconds_count[5m])
```

#### Records Processed per Second
```promql
rate(sap_odata_records_processed_total[5m])
```

#### Error Rate
```promql
rate(sap_odata_errors_total[5m])
```

#### Success Rate
```promql
sum(rate(sap_odata_requests_total{status="success"}[5m])) / sum(rate(sap_odata_requests_total[5m]))
```

---

## 🔍 Monitoring Best Practices

### 1. Use Meaningful Instance Names

```python
# ✅ Good - descriptive instance names
prometheus_instance_name="prod-finance-etl-01"
prometheus_instance_name="dev-sales-pipeline"

# ❌ Bad - generic names
prometheus_instance_name="instance1"
prometheus_instance_name="test"
```

### 2. Group Related Jobs

```python
# All SAP ETL jobs
prometheus_job_name="sap_etl"

# Specific application jobs
prometheus_job_name="finance_reporting"
prometheus_job_name="inventory_sync"
```

### 3. Set Appropriate Push Intervals

```python
# High-frequency queries (many queries per second)
prometheus_push_interval=30  # Push every 30 seconds

# Low-frequency queries (few queries per minute)
prometheus_push_interval=10  # Push every 10 seconds

# Batch jobs (one query every few minutes)
prometheus_push_interval=0   # Push after each query
```

### 4. Monitor Key Metrics

- **Request Duration** - Identify slow queries
- **Error Rate** - Detect connection issues
- **Records Processed** - Track data volume
- **Active Workers** - Monitor concurrency

---

## 🚨 Alerts Configuration

### Example Prometheus Alerts

```yaml
groups:
  - name: sap_odata_connector
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(sap_odata_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in SAP OData Connector"
          description: "Error rate is {{ $value }} errors/sec"
      
      # Slow queries
      - alert: SlowQueries
        expr: rate(sap_odata_request_duration_seconds_sum[5m]) / rate(sap_odata_request_duration_seconds_count[5m]) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow SAP OData queries detected"
          description: "Average query duration is {{ $value }} seconds"
      
      # No data processed
      - alert: NoDataProcessed
        expr: rate(sap_odata_records_processed_total[10m]) == 0
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "No data being processed"
          description: "No records processed in last 15 minutes"
```

---

## 🐛 Troubleshooting

### Metrics Not Appearing in Pushgateway

**Check 1**: Verify Pushgateway URL
```python
# Test connectivity
import requests
response = requests.get("http://localhost:9091/metrics")
print(response.status_code)  # Should be 200
```

**Check 2**: Verify metrics are enabled
```python
config = ClientConfig(
    enable_metrics=True,  # Must be True
    prometheus_pushgateway_url="http://localhost:9091"  # Must be set
)
```

**Check 3**: Check connector logs
```
# Look for:
"Prometheus metrics auto-push enabled"
"Metrics pushed to Prometheus Pushgateway"
```

### Pushgateway Connection Errors

**Solution 1**: Check network connectivity
```bash
curl http://localhost:9091/metrics
```

**Solution 2**: Verify Pushgateway is running
```bash
docker ps | grep pushgateway
```

**Solution 3**: Check firewall rules
```bash
# Ensure port 9091 is accessible
telnet localhost 9091
```

### Metrics Not Updating

**Issue**: Old metrics still showing

**Solution**: Metrics are cumulative (counters). Use `rate()` in Prometheus queries:
```promql
# ✅ Correct - shows rate of change
rate(sap_odata_requests_total[5m])

# ❌ Wrong - shows cumulative total
sap_odata_requests_total
```

---

## 📚 Additional Resources

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Pushgateway Documentation**: https://github.com/prometheus/pushgateway
- **Grafana Dashboards**: https://grafana.com/grafana/dashboards/
- **PromQL Guide**: https://prometheus.io/docs/prometheus/latest/querying/basics/

---

## 🎉 Summary

With automatic Prometheus metrics pushing:

✅ **No manual push code needed** - Just set the Pushgateway URL  
✅ **Metrics pushed automatically** - After each `get_data()` call  
✅ **Production-ready monitoring** - Track performance, errors, and data volume  
✅ **Easy integration** - Works with existing Prometheus/Grafana setups  
✅ **Zero overhead** - Metrics pushed in background, doesn't slow queries  

**Start monitoring your SAP data pipelines in minutes!** 🚀

---

**Package**: `sap-odata-connector-testcov` | **Version**: 1.0.0
