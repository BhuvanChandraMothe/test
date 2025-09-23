# SAP OData Connector

A resilient and high-throughput SAP OData ingestion connector designed to extract data from SAP OData APIs, process it, and store it in structured formats while managing concurrency, retries, and failures.

## Features

- **Resilient Architecture**: Built-in circuit breakers, retry mechanisms, and bulkhead patterns
- **High Throughput**: Concurrent processing with configurable worker pools
- **Intelligent Pagination**: Automatic handling of OData pagination
- **Dependency Management**: Analyzes entity relationships for optimal processing order
- **Dual Storage**: Raw data in GCS, structured data in BigQuery
- **Comprehensive Monitoring**: Prometheus metrics and health checks
- **Error Handling**: Dead letter queue for failed operations
- **Rate Limiting**: Token bucket algorithm for API rate limiting

## Architecture

The connector follows a multi-phase approach:

1. **Discovery Phase**: Fetches metadata, analyzes dependencies, creates execution plan
2. **Execution Phase**: Concurrent data fetching with resilience patterns
3. **Completion Phase**: Final processing and cleanup

### Key Components

- **MetadataService**: Fetches and parses SAP OData metadata (EDMX)
- **CountService**: Queries entity record counts for planning
- **RelationGraphBuilder**: Builds dependency graphs from foreign key relationships
- **PlanGenerator**: Creates optimized execution plans with pagination
- **ProxyPool**: Manages concurrent workers with resilience patterns
- **DataTransformer**: Transforms OData JSON to structured format
- **Storage**: BigQuery for structured data, GCS for raw data
- **Monitoring**: Prometheus metrics and alerting

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a configuration file or use environment variables:

```python
# config.py
SAP_CONNECTOR_SAP_HOST = "your-sap-host.com"
SAP_CONNECTOR_SAP_PORT = 443
SAP_CONNECTOR_SAP_SERVICE_PATH = "/sap/opu/odata/sap/SERVICE_NAME"
SAP_CONNECTOR_USERNAME = "your-username"
SAP_CONNECTOR_PASSWORD = "your-password"
SAP_CONNECTOR_BIGQUERY_PROJECT = "your-gcp-project"
SAP_CONNECTOR_BIGQUERY_DATASET = "sap_odata_data"
SAP_CONNECTOR_GCS_BUCKET = "your-raw-data-bucket"
```

## Usage

### Basic Usage

```python
import asyncio
from sap_odata_connector import create_connector

async def main():
    # Create connector from config
    connector = create_connector("config.py")
    
    # Initialize
    await connector.initialize()
    
    # Run extraction
    stats = await connector.run()
    
    print(f"Processed {stats.records_processed} records")

asyncio.run(main())
```

### Command Line Usage

```bash
# Run full extraction
python -m sap_odata_connector.main --config config.py

# Extract specific entities
python -m sap_odata_connector.main --config config.py --entities EntitySet1 EntitySet2

# Export failed commands
python -m sap_odata_connector.main --export-dlq failed_commands.json

# Retry failed commands
python -m sap_odata_connector.main --retry-failed cmd_id_1 cmd_id_2
```

### Advanced Usage

```python
from sap_odata_connector import SAPODataConnector
from sap_odata_connector.config.models import ClientConfig

# Create custom configuration
config = ClientConfig(
    sap_host="sap-host.com",
    sap_port=443,
    sap_service_path="/sap/opu/odata/sap/SERVICE",
    username="user",
    password="pass",
    bigquery_project="project",
    bigquery_dataset="dataset",
    gcs_bucket="bucket",
    max_workers=20,
    batch_size=2000
)

connector = SAPODataConnector(config)

# Setup callbacks
def on_progress(progress):
    print(f"Queue size: {progress['queue_size']}")

connector.on_progress_update = on_progress

# Run with specific entities
await connector.initialize()
stats = await connector.run(selected_entities=["Users", "Orders"])
```

## Monitoring

The connector exposes Prometheus metrics:

- `sap_odata_requests_total`: Total requests by entity and status
- `sap_odata_request_duration_seconds`: Request duration histogram
- `sap_odata_records_processed_total`: Records processed counter
- `sap_odata_queue_size`: Current queue size
- `sap_odata_active_workers`: Active worker count
- `sap_odata_errors_total`: Error counter by type

### Health Checks

```python
# Check connector health
health_status = await connector.performance_monitor.run_health_checks()
print(health_status)
```

## Error Handling

Failed operations are automatically classified and handled:

- **Retryable Errors**: 5xx errors, timeouts, rate limits
- **Permanent Errors**: 4xx errors (sent to Dead Letter Queue)
- **Circuit Breaker**: Protects against cascading failures

### Dead Letter Queue

```python
# Get failed commands
failed_commands = await connector.dead_letter_queue.get_failed_commands()

# Export for analysis
await connector.export_failed_commands("failed_commands.json")

# Retry specific commands
await connector.retry_failed_commands(["cmd_1", "cmd_2"])
```

## Storage Schema

### BigQuery Tables

Tables are automatically created with schema inferred from OData metadata:

```sql
-- Example table structure
CREATE TABLE `project.dataset.users` (
  entity_name STRING NOT NULL,
  record_id STRING NOT NULL,
  transformed_at TIMESTAMP NOT NULL,
  user_id STRING,
  user_name STRING,
  email STRING,
  metadata JSON
)
PARTITION BY DATE(transformed_at)
```

### GCS Raw Storage

Raw OData responses are stored in GCS with the following structure:

```
gs://bucket/sap_odata_raw/
├── EntityName/
│   └── 2024/01/15/
│       └── 14/
│           └── command_id.json
```

## Performance Tuning

### Configuration Parameters

- `max_workers`: Number of concurrent workers (default: 10)
- `batch_size`: Records per page (default: 1000)
- `requests_per_second`: Rate limit (default: 10.0)

### Optimization Tips

1. **Batch Size**: Larger batches reduce API calls but increase memory usage
2. **Worker Count**: More workers increase throughput but may hit rate limits
3. **Rate Limiting**: Adjust based on SAP system capacity
4. **Entity Selection**: Process only required entities to reduce load

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Check credentials and SAP user permissions
2. **Rate Limiting**: Reduce `requests_per_second` or increase `max_workers`
3. **Memory Issues**: Reduce `batch_size` or `max_workers`
4. **Network Timeouts**: Increase timeout settings in SAP config

### Debugging

Enable debug logging:

```python
import structlog
structlog.configure(level="DEBUG")
```

Check metrics endpoint:

```python
metrics_text = connector.metrics.get_metrics_text()
print(metrics_text)
```

## Development

### Project Structure

```
sap_odata_connector/
├── config/          # Configuration models
├── services/        # Metadata and count services
├── planning/        # Graph builder and plan generator
├── workers/         # Proxy pool and resilience patterns
├── storage/         # Data transformation and storage
├── monitoring/      # Metrics and health monitoring
├── error_handling/  # Dead letter queue and error classification
├── connector.py     # Main orchestrator
└── main.py         # CLI entry point
```

### Running Tests

```bash
pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
