# SAP OData Connector - Logging Guide

## 📋 Overview

The SAP OData Connector provides **comprehensive, informative logging** at every phase of execution. Each log message is designed to help you understand exactly what's happening, troubleshoot issues, and monitor performance.

---

## 🎯 Log Levels

### INFO (Default)
- Connection status and progress
- Query execution details
- Record counts and statistics
- File save locations
- Phase completions

### DEBUG
- Detailed request/response data
- Internal state changes
- Pagination details
- Worker pool activity

### WARNING
- Retries and fallbacks
- Performance degradation
- Non-critical errors

### ERROR
- Connection failures
- Query errors
- Data processing failures

---

## 📊 Execution Phases & Log Messages

### Phase 1: Initialization

```
15:30:01 - odc.connector - INFO - ========================================
15:30:01 - odc.connector - INFO - SAP OData Connector Initialization Started
15:30:01 - odc.connector - INFO - ========================================
15:30:01 - odc.connector - INFO - Configuration loaded [server=sapes5.sapdevcenter.com, port=443, module=ES5, use_https=True]
15:30:01 - odc.connector - INFO - Service URL constructed [url=https://sapes5.sapdevcenter.com:443/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/]
```

**What this tells you:**
- Connector is starting up
- Your configuration is being loaded
- The full OData service URL has been constructed

---

### Phase 2: Connection Testing

```
15:30:02 - odc.connector - INFO - ========================================
15:30:02 - odc.connector - INFO - Phase 1/4: Testing Connection to SAP Server
15:30:02 - odc.connector - INFO - ========================================
15:30:02 - odc.services.metadata - INFO - Attempting connection to SAP OData service [url=https://sapes5.sapdevcenter.com:443/...]
15:30:03 - odc.services.metadata - INFO - ✓ Connection successful [response_time=1.2s, status_code=200]
15:30:03 - odc.connector - INFO - ✓ Connection test passed - SAP server is reachable and credentials are valid
```

**What this tells you:**
- Testing if the SAP server is reachable
- Verifying your credentials work
- How long the connection took
- HTTP status code received

---

### Phase 3: Metadata Retrieval

```
15:30:03 - odc.connector - INFO - ========================================
15:30:03 - odc.connector - INFO - Phase 2/4: Fetching Service Metadata
15:30:03 - odc.connector - INFO - ========================================
15:30:03 - odc.services.metadata - INFO - Downloading OData service metadata [$metadata endpoint]
15:30:05 - odc.services.metadata - INFO - Metadata retrieved successfully [size=245KB, duration=2.1s]
15:30:05 - odc.services.metadata - INFO - Parsing entity schemas and relationships...
15:30:06 - odc.services.metadata - INFO - ✓ Metadata parsing complete [entities=12, relationships=18, properties=156]
15:30:06 - odc.services.metadata - INFO - Entity Relationship diagram saved [file=./output/entity_relationships_20251006_153006.json]
```

**What this tells you:**
- Downloading the service's metadata (schema information)
- How large the metadata is
- Number of entities (tables) available
- Number of relationships (foreign keys) found
- Where the ER diagram was saved

---

### Phase 3: Entity Analysis

```
15:30:06 - odc.connector - INFO - ========================================
15:30:06 - odc.connector - INFO - Phase 3/4: Analyzing Available Entities
15:30:06 - odc.connector - INFO - ========================================
15:30:06 - odc.services.count - INFO - Counting records in all entities...
15:30:07 - odc.services.count - INFO - Entity: Products [records=547]
15:30:07 - odc.services.count - INFO - Entity: Suppliers [records=29]
15:30:08 - odc.services.count - INFO - Entity: Categories [records=8]
15:30:08 - odc.services.count - INFO - Entity: Customers [records=91]
15:30:09 - odc.services.count - INFO - ✓ Record counting complete [total_entities=12, total_records=2,547]
```

**What this tells you:**
- How many entities are available in the service
- How many records each entity contains
- Total data volume available

---

### Phase 4: Worker Pool Setup

```
15:30:09 - odc.connector - INFO - ========================================
15:30:09 - odc.connector - INFO - Phase 4/4: Initializing Worker Pool
15:30:09 - odc.connector - INFO - ========================================
15:30:09 - odc.connector - INFO - Calculating optimal worker configuration...
15:30:09 - odc.connector - INFO - Selected entities for processing [count=4, entities=Products,Suppliers,Categories,Customers]
15:30:09 - odc.connector - INFO - Worker pool configuration [workers=4, connections_per_worker=10, total_connections=40]
15:30:09 - odc.workers.proxy_pool - INFO - Creating worker pool [workers=4]
15:30:10 - odc.workers.proxy_pool - INFO - Worker-1 initialized [status=ready]
15:30:10 - odc.workers.proxy_pool - INFO - Worker-2 initialized [status=ready]
15:30:10 - odc.workers.proxy_pool - INFO - Worker-3 initialized [status=ready]
15:30:10 - odc.workers.proxy_pool - INFO - Worker-4 initialized [status=ready]
15:30:10 - odc.connector - INFO - ✓ Worker pool ready [active_workers=4, connection_pool_size=40]
```

**What this tells you:**
- How many workers will process your queries
- Connection pool size (for parallel requests)
- Which entities you selected for processing
- Each worker's initialization status

---

### Phase 5: Initialization Complete

```
15:30:10 - odc.connector - INFO - ========================================
15:30:10 - odc.connector - INFO - ✓ Connector Initialization Complete
15:30:10 - odc.connector - INFO - ========================================
15:30:10 - odc.connector - INFO - Summary:
15:30:10 - odc.connector - INFO -   • Service URL: https://sapes5.sapdevcenter.com:443/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/
15:30:10 - odc.connector - INFO -   • Total entities available: 12
15:30:10 - odc.connector - INFO -   • Total records available: 2,547
15:30:10 - odc.connector - INFO -   • Selected for processing: 4 entities
15:30:10 - odc.connector - INFO -   • Worker pool: 4 workers with 40 connections
15:30:10 - odc.connector - INFO -   • Initialization time: 9.2 seconds
15:30:10 - odc.connector - INFO - ========================================
15:30:10 - odc.connector - INFO - Ready to execute queries!
15:30:10 - odc.connector - INFO - ========================================
```

**What this tells you:**
- Initialization is complete and successful
- Summary of what's available
- How long initialization took
- System is ready for queries

---

## 🔍 Query Execution Logs

### Simple Query

```
15:30:15 - odc.connector - INFO - ========================================
15:30:15 - odc.connector - INFO - Starting Query Execution
15:30:15 - odc.connector - INFO - ========================================
15:30:15 - odc.connector - INFO - Query parameters:
15:30:15 - odc.connector - INFO -   • Entity: Products
15:30:15 - odc.connector - INFO -   • Filter: None
15:30:15 - odc.connector - INFO -   • Select fields: All
15:30:15 - odc.connector - INFO -   • Expand relations: None
15:30:15 - odc.connector - INFO -   • Order by: None
15:30:15 - odc.connector - INFO -   • Record limit: Unlimited
15:30:15 - odc.connector - INFO - ----------------------------------------
15:30:15 - odc.connector - INFO - Executing paginated query for entity: Products
15:30:15 - odc.workers - INFO - Page 1: Fetched 500 records [duration=0.8s]
15:30:16 - odc.workers - INFO - Page 2: Fetched 47 records [duration=0.6s]
15:30:16 - odc.connector - INFO - ✓ Query completed successfully
15:30:16 - odc.connector - INFO - ----------------------------------------
15:30:16 - odc.connector - INFO - Execution Statistics:
15:30:16 - odc.connector - INFO -   • Total records retrieved: 547
15:30:16 - odc.connector - INFO -   • Total pages fetched: 2
15:30:16 - odc.connector - INFO -   • Total requests made: 2
15:30:16 - odc.connector - INFO -   • Total duration: 1.4 seconds
15:30:16 - odc.connector - INFO -   • Average records/second: 390
15:30:16 - odc.connector - INFO - ----------------------------------------
15:30:16 - odc.storage - INFO - Saving query results to file...
15:30:16 - odc.storage - INFO - ✓ Results saved [file=./output/query_results/20251006_153016_products.json, size=245KB]
15:30:16 - odc.connector - INFO - ========================================
15:30:16 - odc.connector - INFO - ✓ Query Execution Complete
15:30:16 - odc.connector - INFO - ========================================
```

**What this tells you:**
- What query parameters you're using
- Real-time pagination progress
- How many records per page
- Total execution time
- Performance metrics (records/second)
- Where results were saved

---

### Query with Filter

```
15:31:00 - odc.connector - INFO - ========================================
15:31:00 - odc.connector - INFO - Starting Query Execution
15:31:00 - odc.connector - INFO - ========================================
15:31:00 - odc.connector - INFO - Query parameters:
15:31:00 - odc.connector - INFO -   • Entity: Products
15:31:00 - odc.connector - INFO -   • Filter: Price gt 100
15:31:00 - odc.connector - INFO -   • Select fields: Id,Name,Price
15:31:00 - odc.connector - INFO -   • Expand relations: None
15:31:00 - odc.connector - INFO -   • Order by: Price desc
15:31:00 - odc.connector - INFO -   • Record limit: None
15:31:00 - odc.connector - INFO - ----------------------------------------
15:31:00 - odc.connector - INFO - Building OData query URL...
15:31:00 - odc.connector - INFO - Query URL: https://server.com/.../Products?$filter=Price gt 100&$select=Id,Name,Price&$orderby=Price desc
15:31:00 - odc.connector - INFO - ----------------------------------------
15:31:00 - odc.workers - INFO - Page 1: Fetched 247 records [duration=1.1s]
15:31:01 - odc.connector - INFO - ✓ Query completed successfully [records=247, duration=1.1s]
15:31:01 - odc.storage - INFO - ✓ Results saved [file=./output/query_results/20251006_153101_products_filter_Price_greater_100_select_3fields_order_Price_descending.json]
```

**What this tells you:**
- Your filter is being applied
- Which fields you're selecting
- The exact OData URL being queried
- How the filter affected record count
- Descriptive filename based on query parameters

---

### Query with Expansion (JOIN)

```
15:32:00 - odc.connector - INFO - ========================================
15:32:00 - odc.connector - INFO - Starting Query Execution with Relationship Expansion
15:32:00 - odc.connector - INFO - ========================================
15:32:00 - odc.connector - INFO - Query parameters:
15:32:00 - odc.connector - INFO -   • Entity: Products
15:32:00 - odc.connector - INFO -   • Expand relations: Supplier,Category
15:32:00 - odc.connector - INFO - ----------------------------------------
15:32:00 - odc.connector - INFO - Expanding relationships: Supplier, Category
15:32:00 - odc.connector - INFO - This will fetch related data in a single query (like SQL JOIN)
15:32:00 - odc.connector - INFO - ----------------------------------------
15:32:00 - odc.workers - INFO - Page 1: Fetched 500 records with expanded relations [duration=2.3s]
15:32:03 - odc.workers - INFO - Page 2: Fetched 47 records with expanded relations [duration=1.8s]
15:32:04 - odc.connector - INFO - ✓ Query with expansion completed successfully
15:32:04 - odc.connector - INFO - Execution Statistics:
15:32:04 - odc.connector - INFO -   • Main entity records: 547
15:32:04 - odc.connector - INFO -   • Expanded Supplier records: 29 unique suppliers
15:32:04 - odc.connector - INFO -   • Expanded Category records: 8 unique categories
15:32:04 - odc.connector - INFO -   • Total duration: 4.1 seconds
15:32:04 - odc.storage - INFO - ✓ Results saved [file=./output/query_results/20251006_153204_products_expand_Supplier_Category.json, size=512KB]
```

**What this tells you:**
- Relationship expansion is being used (like SQL JOIN)
- Which related entities are being fetched
- How many unique related records were found
- Larger file size due to related data

---

## ⚠️ Error and Warning Logs

### Connection Retry

```
15:35:00 - odc.workers - WARNING - Request failed, attempting retry [attempt=1/3, error=Connection timeout]
15:35:02 - odc.workers - WARNING - Request failed, attempting retry [attempt=2/3, error=Connection timeout]
15:35:04 - odc.workers - INFO - ✓ Request succeeded on retry [attempt=3, duration=1.2s]
```

**What this tells you:**
- A request failed but is being retried
- What error occurred
- Which retry attempt succeeded

### Filter Syntax Error

```
15:36:00 - odc.connector - ERROR - Invalid filter syntax detected
15:36:00 - odc.connector - ERROR - Filter: Price > 100
15:36:00 - odc.connector - ERROR - Error: OData filters use 'gt' not '>'
15:36:00 - odc.connector - ERROR - Correct syntax: Price gt 100
15:36:00 - odc.connector - ERROR - See CONFIGURATION_AND_FILTERING_GUIDE.md for filter syntax reference
```

**What this tells you:**
- Your filter has a syntax error
- What the error is
- How to fix it
- Where to find documentation

### Authentication Failure

```
15:37:00 - odc.services.metadata - ERROR - Authentication failed [status_code=401, response=Unauthorized]
15:37:00 - odc.connector - ERROR - ========================================
15:37:00 - odc.connector - ERROR - Connection Failed: Invalid Credentials
15:37:00 - odc.connector - ERROR - ========================================
15:37:00 - odc.connector - ERROR - Please check:
15:37:00 - odc.connector - ERROR -   1. Username is correct
15:37:00 - odc.connector - ERROR -   2. Password is correct
15:37:00 - odc.connector - ERROR -   3. User has access to this SAP system
15:37:00 - odc.connector - ERROR -   4. SAP client number is correct (if applicable)
15:37:00 - odc.connector - ERROR - ========================================
```

**What this tells you:**
- Authentication failed (401 error)
- Checklist of things to verify
- Clear next steps to resolve

---

## 📈 Performance Monitoring Logs

### High Volume Query

```
15:40:00 - odc.connector - INFO - Starting large data extraction [estimated_records=50,000]
15:40:00 - odc.connector - INFO - This may take several minutes...
15:40:05 - odc.workers - INFO - Progress: 5,000 records (10%) [rate=1,000 records/sec]
15:40:10 - odc.workers - INFO - Progress: 10,000 records (20%) [rate=1,000 records/sec]
15:40:15 - odc.workers - INFO - Progress: 15,000 records (30%) [rate=1,000 records/sec]
...
15:42:30 - odc.connector - INFO - ✓ Large extraction complete [records=50,000, duration=150s, avg_rate=333 records/sec]
```

**What this tells you:**
- Large query is in progress
- Real-time progress updates
- Current processing rate
- Estimated completion time

---

## 🎨 Log Format

### Console Output (Clean & Readable)
```
HH:MM:SS - logger_name - LEVEL - message [key=value, key2=value2]
```

Example:
```
15:30:01 - odc.connector - INFO - Connection successful [server=sapes5.sapdevcenter.com, duration=1.2s]
```

### File Output (Detailed for Debugging)
```
YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - function_name:line - message [key=value]
```

Example:
```
2025-10-06 15:30:01 - odc.connector - INFO - initialize:125 - Connection successful [server=sapes5.sapdevcenter.com, duration=1.2s]
```

---

## 🔧 Customizing Log Level

### In Code

```python
from odc.utils.logging_config import setup_connector_logging

# Set to DEBUG for more detailed logs
setup_connector_logging(log_level="DEBUG")

# Set to WARNING for less verbose logs
setup_connector_logging(log_level="WARNING")
```

### Via Environment Variable

```bash
export SAP_CONNECTOR_LOG_LEVEL="DEBUG"
```

---

## 📁 Log Files

### Location
```
./logs/sap_odata_connector_YYYYMMDD_HHMMSS.log
```

### Rotation
- Maximum file size: 10MB
- Backup files kept: 5
- Old logs automatically archived

### Example
```
./logs/
├── sap_odata_connector_20251006_153001.log      (current)
├── sap_odata_connector_20251006_153001.log.1    (backup)
├── sap_odata_connector_20251006_153001.log.2    (backup)
└── ...
```

---

## 💡 Understanding Log Messages

### ✓ Success Indicators
- `✓` symbol indicates successful completion
- Green checkmarks in terminal (if supported)
- "completed successfully" messages

### ⚠️ Warning Indicators
- `WARNING` level
- Retry attempts
- Performance degradation notices

### ❌ Error Indicators
- `ERROR` level
- Failure messages
- Troubleshooting suggestions

### 📊 Progress Indicators
- Percentage complete
- Records processed
- Time remaining estimates

---

## 🎯 Best Practices

### 1. Monitor Initialization Logs
```
✓ Check all 4 phases complete successfully
✓ Verify entity counts match expectations
✓ Confirm worker pool size is appropriate
```

### 2. Watch Query Execution Logs
```
✓ Verify filter syntax is correct
✓ Check record counts are as expected
✓ Monitor performance metrics
```

### 3. Review Error Logs
```
✓ Read the full error message
✓ Check suggested solutions
✓ Refer to documentation links
```

### 4. Track Performance
```
✓ Monitor records/second rate
✓ Check request duration
✓ Watch for retry warnings
```

---

## 📚 Log Message Categories

| Category | Example | What It Means |
|----------|---------|---------------|
| **Configuration** | `Configuration loaded [server=...]` | Your settings are being applied |
| **Connection** | `✓ Connection successful` | SAP server is reachable |
| **Metadata** | `Metadata retrieved [entities=12]` | Service schema downloaded |
| **Query** | `Executing query for entity: Products` | Data query starting |
| **Pagination** | `Page 1: Fetched 500 records` | Automatic pagination in progress |
| **Storage** | `Results saved [file=...]` | Data saved to disk |
| **Performance** | `Duration: 1.4s, Rate: 390 records/sec` | Performance metrics |
| **Error** | `Authentication failed` | Something went wrong |
| **Warning** | `Request failed, retrying...` | Non-critical issue, being handled |

---

## 🆘 Troubleshooting with Logs

### Problem: Slow Queries

**Look for:**
```
15:30:16 - odc.connector - WARNING - Query taking longer than expected [duration=30s, expected=<10s]
15:30:16 - odc.connector - INFO - Consider adding filters to reduce data volume
```

**Solution:** Add filters to your query

### Problem: Connection Issues

**Look for:**
```
15:30:00 - odc.workers - WARNING - Connection timeout [attempt=1/3]
15:30:02 - odc.workers - WARNING - Connection timeout [attempt=2/3]
```

**Solution:** Check network connectivity, firewall rules

### Problem: No Data Returned

**Look for:**
```
15:30:10 - odc.connector - INFO - Query completed [records=0]
15:30:10 - odc.connector - WARNING - No records matched your filter criteria
15:30:10 - odc.connector - INFO - Filter used: Status eq 'NonExistent'
```

**Solution:** Check your filter syntax and values

---

## 🎉 Summary

The SAP OData Connector provides:

✅ **Clear phase-by-phase progress** - Know exactly what's happening  
✅ **Detailed error messages** - Understand what went wrong  
✅ **Performance metrics** - Monitor query efficiency  
✅ **Helpful suggestions** - Get guidance on fixing issues  
✅ **File locations** - Know where your data is saved  
✅ **Real-time progress** - Track long-running queries  

**Every log message is designed to help you succeed!** 🚀

---

**Package**: `sap-odata-connector-testcov` | **Version**: 1.0.0
