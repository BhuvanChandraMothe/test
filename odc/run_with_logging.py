#!/usr/bin/env python3
"""
Run SAP OData Connector with enhanced logging to see all logs and metrics
"""

import sys
import asyncio
import structlog
from odc.config.models import ClientConfig
from odc.connector import SAPODataConnector

# Configure structured logging for better visibility
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG level
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

async def run_connector_with_logging():
    """Run connector with full logging enabled"""
    
    logger = structlog.get_logger("sap_odata_demo")
    
    logger.info("Starting SAP OData Connector with full logging")
    
    # Configure for Northwind service
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Categories", "Products"],  # Small subset for demo
        batch_size=10,  # Small batches to see more log entries
        max_workers=2,
        requests_per_second=1.0,  # Slow rate to see individual requests
        output_directory="./demo_output"
    )
    
    logger.info("Configuration loaded", 
                service_url=config.odata_service_url,
                entities=config.selected_modules,
                batch_size=config.batch_size)
    
    # Create connector
    connector = SAPODataConnector(config)
    
    # Add progress callback to see real-time updates
    def progress_callback(entity_name: str, records_count: int):
        logger.info("Progress update", 
                   entity=entity_name, 
                   records_fetched=records_count)
    
    connector.on_progress_update = progress_callback
    
    try:
        # Run the connector
        logger.info("Starting data extraction")
        await connector.run()
        logger.info("Data extraction completed successfully")
        
        # Show final metrics
        if hasattr(connector, 'metrics') and connector.metrics:
            logger.info("Final metrics summary")
            stats = connector.metrics.get_summary_stats()
            for key, value in stats.items():
                logger.info("Metric", name=key, value=value)
    
    except Exception as e:
        logger.error("Connector execution failed", error=str(e), exc_info=True)
    
    finally:
        logger.info("Connector execution finished")

if __name__ == "__main__":
    asyncio.run(run_connector_with_logging())
