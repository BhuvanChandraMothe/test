# SAP OData Connector - Documentation Index

## Overview
This directory contains comprehensive documentation for the SAP OData Connector, a production-ready Python application for extracting data from SAP OData services. Each file is documented with detailed explanations of concepts, design patterns, and usage examples.

## Documentation Structure

### Core Application Files
1. **[01_main.py.md](01_main.py.md)** - CLI Entry Point
   - Command-line interface design
   - Logging configuration
   - Async main pattern
   - Configuration loading
   - Progress reporting

2. **[02_connector.py.md](02_connector.py.md)** - Main Orchestrator
   - Service orchestration
   - Async lifecycle management
   - Discovery and execution phases
   - Error handling and cleanup
   - Progress callbacks

### Configuration and Models
3. **[03_config_models.py.md](03_config_models.py.md)** - Configuration Management
   - Pydantic data validation
   - Environment variable integration
   - Configuration hierarchies
   - Type safety patterns
   - Factory methods

### Services Layer
4. **[04_services_metadata.py.md](04_services_metadata.py.md)** - Metadata Service
   - OData EDMX parsing
   - XML namespace handling
   - Entity schema extraction
   - Relationship mapping
   - Version compatibility (V2/V4)

5. **[05_services_count.py.md](05_services_count.py.md)** - Count Service
   - Concurrent count fetching
   - Fallback strategies (V4 → V2)
   - Semaphore-based rate limiting
   - Sample data retrieval
   - Error isolation

### Planning and Execution
6. **[06_planning_plan_generator.py.md](06_planning_plan_generator.py.md)** - Execution Planning
   - Dependency-aware planning
   - Priority-based scheduling
   - Pagination strategies
   - Topological sorting
   - Adaptive batch sizing

### Worker Pool and Resilience
7. **[07_workers_proxy_pool.py.md](07_workers_proxy_pool.py.md)** - HTTP Worker Pool
   - Concurrent HTTP processing
   - Connection pool management
   - Statistics tracking
   - Progress callbacks
   - Resource management

8. **[08_workers_resilience.py.md](08_workers_resilience.py.md)** - Resilience Patterns
   - Token bucket rate limiting
   - Circuit breaker pattern
   - Exponential backoff retry
   - Pattern composition
   - Adaptive rate limiting

### Storage and Transformation
9. **[09_storage_local.py.md](09_storage_local.py.md)** - Local File Storage
   - Hierarchical directory structure
   - Async file I/O
   - Metadata persistence
   - Batch operations
   - Storage statistics

10. **[10_transformation_data_transformer.py.md](10_transformation_data_transformer.py.md)** - Data Transformation
    - Rule-based transformations
    - Type conversion and validation
    - Data cleaning operations
    - Schema-based validation
    - Custom transformation functions

### Monitoring and Error Handling
11. **[11_monitoring_metrics.py.md](11_monitoring_metrics.py.md)** - Metrics and Monitoring
    - Time-series metrics collection
    - Performance monitoring
    - Alert management
    - Metrics export (Prometheus, JSON)
    - Health checks

12. **[12_error_handling_dead_letter_queue.py.md](12_error_handling_dead_letter_queue.py.md)** - Error Handling
    - Error classification and severity
    - Dead letter queue management
    - Retry logic with backoff
    - Persistent error storage
    - Error analysis and reporting

## Key Programming Concepts Covered

### Asynchronous Programming
- **Event Loop Management**: Proper async/await patterns
- **Concurrent Processing**: Managing multiple HTTP requests
- **Resource Management**: Context managers for cleanup
- **Task Coordination**: Producer-consumer patterns
- **Non-blocking I/O**: File operations and HTTP requests

### Enterprise Patterns
- **Dependency Injection**: Loose coupling of components
- **Factory Pattern**: Object creation and configuration
- **Observer Pattern**: Progress callbacks and events
- **Strategy Pattern**: Configurable algorithms
- **Circuit Breaker**: Fault tolerance and resilience

### Data Processing
- **ETL Pipeline**: Extract, Transform, Load operations
- **Schema Validation**: Type safety and data integrity
- **Batch Processing**: Efficient bulk operations
- **Streaming**: Memory-efficient data handling
- **Caching**: Performance optimization

### Monitoring and Observability
- **Metrics Collection**: Performance and business metrics
- **Structured Logging**: Contextual log information
- **Health Checks**: System status monitoring
- **Alerting**: Threshold-based notifications
- **Error Tracking**: Comprehensive error management

### Configuration Management
- **Environment Variables**: 12-factor app principles
- **Configuration Validation**: Type-safe configuration
- **Hierarchical Config**: Multiple configuration sources
- **Secret Management**: Secure credential handling

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI (main)    │───▶│   Connector     │───▶│  Services       │
│                 │    │  (Orchestrator) │    │  - Metadata     │
└─────────────────┘    └─────────────────┘    │  - Count        │
                                              └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐           ▼
│   Storage       │◀───│  Transformation │    ┌─────────────────┐
│  - Local Files  │    │  - Data Cleaning│    │   Planning      │
│  - Metadata     │    │  - Validation   │    │  - Dependencies │
└─────────────────┘    └─────────────────┘    │  - Scheduling   │
                                              └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐           ▼
│   Monitoring    │    │  Error Handling │    ┌─────────────────┐
│  - Metrics      │    │  - Dead Letter  │    │  Worker Pool    │
│  - Alerts       │    │  - Retry Logic  │    │  - HTTP Clients │
│  - Health       │    │  - Classification│   │  - Resilience   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Usage Patterns

### Basic Usage
```python
from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig

config = ClientConfig(
    odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
    batch_size=1000,
    max_workers=5
)

connector = SAPODataConnector(config)
await connector.run()
```

### Advanced Configuration
```python
config = ClientConfig(
    odata_service_url="https://my-sap-system.com/service/",
    username="user",
    password="pass",
    selected_modules=["Products", "Orders"],
    batch_size=2000,
    max_workers=10,
    requests_per_second=10.0,
    output_directory="./sap_data"
)
```

### Custom Transformations
```python
from odc.transformation.data_transformer import TransformationRule

rules = [
    TransformationRule(
        field_name="email",
        rule_type="validate",
        parameters={"validation_type": "email"},
        error_action="skip"
    )
]

connector.transformer.add_transformation_rules("Customers", rules)
```

## Best Practices

### Performance
- Use appropriate batch sizes (1000-5000 records)
- Limit concurrent workers based on server capacity
- Implement proper rate limiting
- Monitor memory usage for large datasets

### Reliability
- Configure retry logic with exponential backoff
- Use circuit breakers for failing services
- Implement comprehensive error handling
- Monitor system health and metrics

### Security
- Store credentials in environment variables
- Use HTTPS for all communications
- Validate all input data
- Log security events appropriately

### Maintainability
- Follow the documented patterns
- Use structured logging
- Implement comprehensive tests
- Document configuration changes

## Troubleshooting

### Common Issues
1. **Connection Timeouts**: Increase timeout values or reduce batch sizes
2. **Rate Limiting**: Implement proper rate limiting and backoff
3. **Memory Issues**: Process data in smaller batches
4. **Authentication Failures**: Verify credentials and permissions

### Debugging
- Enable debug logging for detailed information
- Check dead letter queue for failed operations
- Monitor metrics for performance issues
- Review error classifications and patterns

## Contributing

When extending the connector:
1. Follow the established patterns documented here
2. Add comprehensive error handling
3. Include metrics and monitoring
4. Write detailed documentation
5. Add appropriate tests

## Dependencies

### Core Libraries
- **httpx**: Async HTTP client
- **asyncio**: Asynchronous programming
- **pydantic**: Data validation
- **structlog**: Structured logging

### Optional Libraries
- **psutil**: System metrics
- **pandas**: Data processing
- **pyarrow**: Parquet support
- **prometheus_client**: Metrics export

This documentation provides a complete understanding of the SAP OData Connector architecture, patterns, and usage for effective maintenance and extension.
