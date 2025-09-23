#!/usr/bin/env python3
"""
Run SAP OData Connector with enhanced logging to both file and terminal
"""

import sys
import asyncio
import structlog
import logging
from datetime import datetime
from pathlib import Path

# Add the odc directory to Python path
sys.path.append('./odc')

from config.models import ClientConfig
from connector import SAPODataConnector

def setup_dual_logging():
    """Setup logging to both file and console"""
    
    # Create logs directory
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"sap_odata_connector_{timestamp}.log"
    
    # Configure Python's standard logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configure structlog for structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)  # For console
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG level
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return str(log_file)

async def test_different_configurations():
    """Test different worker/batch size configurations to investigate record count differences"""
    
    log_file = setup_dual_logging()
    logger = structlog.get_logger("config_test")
    
    logger.info("Starting configuration comparison test", log_file=log_file)
    
    # Test configurations
    test_configs = [
        {
            "name": "Small Batch, Few Workers",
            "batch_size": 10,
            "max_workers": 2,
            "requests_per_second": 2.0,
            "total_records_limit": 100
        },
        {
            "name": "Medium Batch, Medium Workers", 
            "batch_size": 50,
            "max_workers": 5,
            "requests_per_second": 5.0,
            "total_records_limit": 100
        },
        {
            "name": "Large Batch, Many Workers",
            "batch_size": 100,
            "max_workers": 10,
            "requests_per_second": 10.0,
            "total_records_limit": 100
        }
    ]
    
    results = {}
    
    for test_config in test_configs:
        logger.info("Testing configuration", config=test_config)
        
        # Create configuration
        config = ClientConfig(
            odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
            selected_modules=["Products"],  # Single entity for focused testing
            batch_size=test_config["batch_size"],
            max_workers=test_config["max_workers"],
            requests_per_second=test_config["requests_per_second"],
            total_records_limit=test_config["total_records_limit"],
            output_directory=f"./test_output_{test_config['name'].replace(' ', '_').lower()}"
        )
        
        # Track records processed
        records_processed = 0
        
        def progress_callback(entity_name: str, records_count: int):
            nonlocal records_processed
            records_processed = records_count
            logger.info("Progress update", 
                       config_name=test_config["name"],
                       entity=entity_name, 
                       records_fetched=records_count)
        
        try:
            # Create and run connector
            connector = SAPODataConnector(config)
            connector.on_progress_update = progress_callback
            
            logger.info("Starting connector execution", config_name=test_config["name"])
            await connector.run()
            
            # Get final metrics
            execution_summary = connector.get_execution_summary()
            
            results[test_config["name"]] = {
                "config": test_config,
                "records_processed": records_processed,
                "execution_summary": execution_summary,
                "success": True
            }
            
            logger.info("Configuration test completed", 
                       config_name=test_config["name"],
                       records_processed=records_processed,
                       execution_summary=execution_summary)
            
        except Exception as e:
            logger.error("Configuration test failed", 
                        config_name=test_config["name"],
                        error=str(e), 
                        exc_info=True)
            
            results[test_config["name"]] = {
                "config": test_config,
                "records_processed": records_processed,
                "error": str(e),
                "success": False
            }
    
    # Compare results
    logger.info("=== CONFIGURATION COMPARISON RESULTS ===")
    for config_name, result in results.items():
        logger.info("Result summary",
                   config_name=config_name,
                   success=result["success"],
                   records_processed=result["records_processed"],
                   batch_size=result["config"]["batch_size"],
                   max_workers=result["config"]["max_workers"])
    
    # Analyze differences
    record_counts = [r["records_processed"] for r in results.values() if r["success"]]
    if len(set(record_counts)) > 1:
        logger.warning("ISSUE DETECTED: Different configurations produced different record counts!",
                      record_counts=record_counts)
        logger.info("This suggests a potential issue with pagination, rate limiting, or worker coordination")
    else:
        logger.info("All configurations produced consistent record counts", 
                   consistent_count=record_counts[0] if record_counts else 0)
    
    logger.info("Test completed. Check log file for detailed analysis", log_file=log_file)
    return results

if __name__ == "__main__":
    asyncio.run(test_different_configurations())
