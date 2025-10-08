"""Main entry point for SAP OData Connector"""

import asyncio
import sys
import argparse
from pathlib import Path
import structlog
from typing import Optional

from .connector import create_connector, SAPODataConnector
from .config.models import ConnectorSettings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SAP OData Connector")
    parser.add_argument(
        "--config", 
        type=str, 
        help="Configuration file path"
    )
    parser.add_argument(
        "--entities", 
        type=str, 
        nargs="+", 
        help="Specific entities to process"
    )
    parser.add_argument(
        "--export-dlq", 
        type=str, 
        help="Export dead letter queue to file"
    )
    parser.add_argument(
        "--retry-failed", 
        type=str, 
        nargs="+", 
        help="Retry specific failed command IDs"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Perform dry run without actual execution"
    )
    
    args = parser.parse_args()
    
    try:
        # Create connector
        connector = create_connector(args.config)
        
        # Initialize
        await connector.initialize()
        
        if args.export_dlq:
            # Export dead letter queue
            await connector.export_failed_commands(args.export_dlq)
            logger.info("Dead letter queue exported", file_path=args.export_dlq)
            return
        
        if args.retry_failed:
            # Retry failed commands
            retried_count = await connector.retry_failed_commands(args.retry_failed)
            logger.info("Failed commands retried", count=retried_count)
            return
        
        if args.dry_run:
            logger.info("Dry run mode - skipping actual execution")
            return
        
        # Setup progress callback
        def progress_callback(progress_info):
            logger.info("Execution progress", **progress_info)
        
        connector.on_progress_update = progress_callback
        
        # Run connector
        stats = await connector.run(selected_entities=args.entities)
        
        # Print summary
        summary = connector.get_execution_summary()
        logger.info("Execution completed", summary=summary)
        
    except KeyboardInterrupt:
        logger.info("Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Execution failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
