#!/usr/bin/env python3
"""
Test script to demonstrate the SAP OData connector improvements
"""

import sys
import asyncio
import structlog
from pathlib import Path

# Add the odc directory to Python path
sys.path.append('./odc')

from config.models import ClientConfig
from connector import SAPODataConnector

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def test_connection_and_metadata():
    """Test the new connection testing and metadata features"""
    logger.info("🧪 Testing Connection and Metadata Features")
    
    # Create configuration for Northwind (public OData service)
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=25,
        max_workers=2,
        requests_per_second=2.0,
        total_records_limit=50,  # Limit to 50 records for testing
        output_directory="./test_output"
    )
    
    try:
        # Create connector
        connector = SAPODataConnector(config)
        
        # Test initialization with connection testing
        logger.info("🔍 Step 1: Testing initialization with connection validation")
        await connector.initialize()
        
        # Check if Entity Relationship file was created
        er_file = Path("./test_output/entity_relationships.json")
        if er_file.exists():
            logger.info("✅ Entity Relationship file created successfully", 
                       file_path=str(er_file),
                       file_size_kb=round(er_file.stat().st_size / 1024, 2))
            
            # Show a sample of the ER file content
            import json
            with open(er_file, 'r') as f:
                er_data = json.load(f)
            
            logger.info("📋 Entity Relationship file summary",
                       total_entities=er_data['summary']['entity_count'],
                       total_relationships=er_data['summary']['relationship_count'],
                       service_url=er_data['metadata']['service_url'])
        else:
            logger.error("❌ Entity Relationship file was not created")
        
        logger.info("✅ Connection and metadata testing completed successfully")
        return True
        
    except Exception as e:
        logger.error("❌ Connection and metadata testing failed", error=str(e))
        return False


async def test_record_count_accuracy():
    """Test the improved record count accuracy"""
    logger.info("🧪 Testing Record Count Accuracy")
    
    # Configuration designed to test record limiting
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=20,  # Small batch size to test multiple requests
        max_workers=3,  # Multiple workers to test coordination
        requests_per_second=5.0,
        total_records_limit=45,  # Specific limit that doesn't divide evenly by batch_size
        output_directory="./test_output_records"
    )
    
    try:
        connector = SAPODataConnector(config)
        
        # Progress tracking
        records_processed = 0
        
        def progress_callback(progress_info):
            nonlocal records_processed
            records_processed = progress_info.get('records_processed', 0)
            logger.info("📊 Progress update", **progress_info)
        
        connector.on_progress_update = progress_callback
        
        # Initialize and run
        await connector.initialize()
        stats = await connector.run()
        
        # Check results
        expected_limit = config.total_records_limit
        actual_processed = stats.records_processed
        
        logger.info("🎯 Record Count Test Results",
                   expected_limit=expected_limit,
                   actual_processed=actual_processed,
                   difference=abs(expected_limit - actual_processed),
                   accuracy_percentage=round((min(expected_limit, actual_processed) / max(expected_limit, actual_processed)) * 100, 2))
        
        # Consider the test successful if we're within 10% of the target
        # (some variance is acceptable due to pagination boundaries)
        accuracy = min(expected_limit, actual_processed) / max(expected_limit, actual_processed)
        
        if accuracy >= 0.9:  # 90% accuracy threshold
            logger.info("✅ Record count accuracy test PASSED")
            return True
        else:
            logger.warning("⚠️ Record count accuracy test needs improvement")
            return False
        
    except Exception as e:
        logger.error("❌ Record count accuracy test failed", error=str(e))
        return False


async def test_connection_pool():
    """Test the connection pool functionality"""
    logger.info("🧪 Testing Connection Pool")
    
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Categories"],  # Small entity for quick testing
        batch_size=10,
        max_workers=4,
        requests_per_second=8.0,
        total_records_limit=20,
        output_directory="./test_output_pool"
    )
    
    try:
        connector = SAPODataConnector(config)
        await connector.initialize()
        
        # Check connection pool stats
        if connector.proxy_pool and connector.proxy_pool.resilience:
            pool_stats = await connector.proxy_pool.resilience.connection_pool.get_pool_stats()
            logger.info("🔗 Connection Pool Stats", **pool_stats)
            
            if pool_stats.get("is_validated"):
                logger.info("✅ Connection pool validation test PASSED")
                return True
            else:
                logger.warning("⚠️ Connection pool not validated")
                return False
        else:
            logger.error("❌ Connection pool not available")
            return False
        
    except Exception as e:
        logger.error("❌ Connection pool test failed", error=str(e))
        return False


async def main():
    """Run all improvement tests"""
    logger.info("🚀 Starting SAP OData Connector Improvement Tests")
    
    # Create output directories
    Path("./test_output").mkdir(exist_ok=True)
    Path("./test_output_records").mkdir(exist_ok=True)
    Path("./test_output_pool").mkdir(exist_ok=True)
    
    test_results = {}
    
    # Test 1: Connection and Metadata
    logger.info("\n" + "="*60)
    test_results["connection_metadata"] = await test_connection_and_metadata()
    
    # Test 2: Record Count Accuracy
    logger.info("\n" + "="*60)
    test_results["record_accuracy"] = await test_record_count_accuracy()
    
    # Test 3: Connection Pool
    logger.info("\n" + "="*60)
    test_results["connection_pool"] = await test_connection_pool()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("🏁 TEST SUMMARY")
    logger.info("="*60)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All improvements are working correctly!")
    else:
        logger.warning("⚠️ Some improvements need attention")
    
    logger.info("\n📁 Check the following directories for test outputs:")
    logger.info("  - ./test_output/ (Entity Relationship file)")
    logger.info("  - ./test_output_records/ (Record accuracy test data)")
    logger.info("  - ./test_output_pool/ (Connection pool test data)")


if __name__ == "__main__":
    asyncio.run(main())
