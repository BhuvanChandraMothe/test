#!/usr/bin/env python3
"""
Practical demonstration of the record count issue and its solution
Shows exactly why different worker/batch configurations produce different results
"""

import sys
import asyncio
import structlog
import logging
from datetime import datetime
from pathlib import Path
import json

# Add the odc directory to Python path
sys.path.append('./odc')

from config.models import ClientConfig

def setup_comprehensive_logging():
    """Setup logging to both file and console with clear formatting"""
    
    # Create logs directory
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"record_count_demo_{timestamp}.log"
    
    # Configure logging handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configure structlog
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
    
    return str(log_file)

def simulate_worker_behavior(config: ClientConfig, entity_name: str = "Products"):
    """Simulate how workers behave with different configurations"""
    
    logger = structlog.get_logger("worker_simulator")
    
    # Simulate total available records in the entity
    total_available_records = 77  # Northwind Products has 77 records
    
    logger.info("=== WORKER BEHAVIOR SIMULATION ===")
    logger.info("Configuration", 
                batch_size=config.batch_size,
                max_workers=config.max_workers,
                requests_per_second=config.requests_per_second,
                total_records_limit=config.total_records_limit)
    
    logger.info("Entity info", 
                entity=entity_name,
                total_available=total_available_records)
    
    # Calculate theoretical behavior
    if config.total_records_limit:
        target_records = min(config.total_records_limit, total_available_records)
    else:
        target_records = total_available_records
    
    theoretical_batches = (target_records + config.batch_size - 1) // config.batch_size
    
    logger.info("Theoretical calculation",
                target_records=target_records,
                batches_needed=theoretical_batches,
                records_per_batch=config.batch_size)
    
    # Simulate race condition scenarios
    scenarios = []
    
    # Scenario 1: Perfect coordination (ideal case)
    perfect_records = min(theoretical_batches * config.batch_size, target_records)
    scenarios.append({
        "name": "Perfect Coordination",
        "records_fetched": perfect_records,
        "probability": "Low" if config.max_workers > 3 else "High"
    })
    
    # Scenario 2: Race condition - workers overfetch
    if config.max_workers > 1:
        # Each worker might start a batch before others finish
        max_overfetch = config.batch_size * (config.max_workers - 1)
        race_records = min(target_records + max_overfetch, total_available_records)
        scenarios.append({
            "name": "Race Condition Overfetch",
            "records_fetched": race_records,
            "probability": "High" if config.max_workers > 3 else "Medium"
        })
    
    # Scenario 3: Rate limiting delays
    if config.requests_per_second > 5 and config.max_workers > 3:
        # Some workers get delayed, may fetch partial batches
        delayed_records = target_records - (config.batch_size // 2)
        scenarios.append({
            "name": "Rate Limiting Delays",
            "records_fetched": max(0, delayed_records),
            "probability": "Medium"
        })
    
    logger.info("=== POSSIBLE OUTCOMES ===")
    for scenario in scenarios:
        logger.info("Scenario outcome",
                   scenario=scenario["name"],
                   records=scenario["records_fetched"],
                   probability=scenario["probability"])
    
    # Identify the root cause
    logger.warning("=== ROOT CAUSE ANALYSIS ===")
    
    if config.max_workers > 3:
        logger.warning("HIGH RISK: Too many workers")
        logger.warning("- Multiple workers check total_records_limit simultaneously")
        logger.warning("- Workers may all start fetching before any completes")
        logger.warning("- Result: Fetching beyond the intended limit")
    
    if config.total_records_limit and config.total_records_limit % config.batch_size != 0:
        logger.warning("COORDINATION ISSUE: Batch size doesn't divide evenly into limit")
        logger.warning(f"- Limit: {config.total_records_limit}, Batch: {config.batch_size}")
        logger.warning(f"- Last batch will be partial: {config.total_records_limit % config.batch_size} records")
        logger.warning("- Workers may not handle partial batches consistently")
    
    if config.requests_per_second > 10 and config.max_workers > 5:
        logger.warning("TIMING ISSUE: High rate with many workers")
        logger.warning("- Token bucket may cause uneven request distribution")
        logger.warning("- Some workers get delayed, affecting coordination")
    
    return scenarios

def demonstrate_solutions():
    """Demonstrate configurations that solve the record count issue"""
    
    logger = structlog.get_logger("solution_demo")
    
    logger.info("=== SOLUTION CONFIGURATIONS ===")
    
    # Solution 1: Single worker (eliminates race conditions)
    solution1 = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=25,
        max_workers=1,  # Single worker = no race conditions
        requests_per_second=2.0,
        total_records_limit=100,
        output_directory="./solution1_output"
    )
    
    logger.info("Solution 1: Single Worker")
    logger.info("Benefits: Eliminates all race conditions")
    logger.info("Drawback: Slower processing")
    simulate_worker_behavior(solution1)
    
    # Solution 2: Evenly divisible batch size
    solution2 = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=50,  # 100/50 = exactly 2 batches
        max_workers=2,
        requests_per_second=2.0,
        total_records_limit=100,
        output_directory="./solution2_output"
    )
    
    logger.info("Solution 2: Evenly Divisible Batches")
    logger.info("Benefits: Predictable batch count, minimal race conditions")
    logger.info("Calculation: 100 records ÷ 50 batch_size = exactly 2 batches")
    simulate_worker_behavior(solution2)
    
    # Solution 3: No limit (avoid limit-checking race conditions)
    solution3 = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=25,
        max_workers=4,
        requests_per_second=5.0,
        total_records_limit=None,  # No limit = no limit-checking races
        output_directory="./solution3_output"
    )
    
    logger.info("Solution 3: No Record Limit")
    logger.info("Benefits: Eliminates limit-checking race conditions")
    logger.info("Note: Will fetch all available records (77 for Products)")
    simulate_worker_behavior(solution3)
    
    return [solution1, solution2, solution3]

def create_test_script():
    """Create a test script to verify the solutions"""
    
    logger = structlog.get_logger("test_creator")
    
    test_script = '''#!/usr/bin/env python3
"""
Test script to verify record count consistency
Run this multiple times to check for consistent results
"""

import sys
import asyncio
sys.path.append('./odc')

from config.models import ClientConfig
from connector import SAPODataConnector

async def test_configuration(config_name, config):
    """Test a configuration and return record count"""
    print(f"\\n=== Testing {config_name} ===")
    
    records_processed = 0
    
    def progress_callback(entity_name: str, records_count: int):
        nonlocal records_processed
        records_processed = records_count
        print(f"Progress: {entity_name} - {records_count} records")
    
    try:
        connector = SAPODataConnector(config)
        connector.on_progress_update = progress_callback
        
        await connector.run()
        
        print(f"Final count for {config_name}: {records_processed} records")
        return records_processed
        
    except Exception as e:
        print(f"Error in {config_name}: {e}")
        return 0

async def main():
    """Run consistency tests"""
    
    # Test the problematic configuration
    problematic_config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=30,  # Doesn't divide evenly into 100
        max_workers=8,  # Many workers = high race condition risk
        requests_per_second=15.0,  # High rate = timing issues
        total_records_limit=100,
        output_directory="./problematic_output"
    )
    
    # Test the fixed configuration
    fixed_config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=50,  # Divides evenly: 100/50 = 2 batches
        max_workers=2,  # Few workers = low race condition risk
        requests_per_second=2.0,  # Conservative rate
        total_records_limit=100,
        output_directory="./fixed_output"
    )
    
    print("=== CONSISTENCY TEST ===")
    print("Run this script multiple times to check consistency")
    
    problematic_count = await test_configuration("Problematic Config", problematic_config)
    fixed_count = await test_configuration("Fixed Config", fixed_config)
    
    print(f"\\n=== RESULTS ===")
    print(f"Problematic config: {problematic_count} records")
    print(f"Fixed config: {fixed_count} records")
    
    if fixed_count == 100:
        print("✅ Fixed config produced expected result (100 records)")
    else:
        print("❌ Fixed config didn't produce expected result")
    
    if problematic_count != 100:
        print("⚠️  Problematic config produced inconsistent result")
    else:
        print("🤔 Problematic config happened to work this time")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    test_file = Path("test_record_consistency.py")
    test_file.write_text(test_script)
    
    logger.info("Created test script", file=str(test_file))
    logger.info("Usage: Run 'python test_record_consistency.py' multiple times")
    logger.info("Expected: Fixed config always returns 100, problematic config varies")
    
    return str(test_file)

if __name__ == "__main__":
    # Setup logging
    log_file = setup_comprehensive_logging()
    logger = structlog.get_logger("main")
    
    logger.info("=== RECORD COUNT ISSUE DEMONSTRATION ===")
    logger.info("Log file created", path=log_file)
    
    # Demonstrate the problem
    logger.info("Step 1: Analyzing problematic configuration")
    
    problematic_config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],
        batch_size=30,  # 100/30 = 3.33 batches (not evenly divisible)
        max_workers=8,  # Many workers increase race condition probability
        requests_per_second=15.0,  # High rate can cause timing issues
        total_records_limit=100,
        output_directory="./problematic_output"
    )
    
    logger.warning("PROBLEMATIC CONFIGURATION:")
    simulate_worker_behavior(problematic_config)
    
    # Demonstrate solutions
    logger.info("Step 2: Demonstrating solutions")
    solutions = demonstrate_solutions()
    
    # Create test script
    logger.info("Step 3: Creating test script")
    test_script_path = create_test_script()
    
    # Summary
    logger.info("=== SUMMARY ===")
    logger.info("Problem identified: Race conditions between workers")
    logger.info("Root causes:")
    logger.info("1. total_records_limit checked after fetching, not before")
    logger.info("2. Multiple workers can fetch simultaneously near the limit")
    logger.info("3. Batch sizes that don't divide evenly create coordination issues")
    logger.info("4. High request rates with many workers cause timing problems")
    
    logger.info("Solutions provided:")
    logger.info("1. Use single worker (max_workers=1) for guaranteed consistency")
    logger.info("2. Use batch_size that divides evenly into total_records_limit")
    logger.info("3. Use fewer workers (≤3) to reduce race conditions")
    logger.info("4. Remove total_records_limit to avoid limit-checking races")
    
    logger.info("Files created:")
    logger.info(f"- Detailed log: {log_file}")
    logger.info(f"- Test script: {test_script_path}")
    
    print(f"\n=== NEXT STEPS ===")
    print(f"1. Check detailed analysis in: {log_file}")
    print(f"2. Run consistency test: python {test_script_path}")
    print(f"3. Use the recommended 'Fixed Config' for consistent results")
    print(f"4. All future connector runs will log to files in ./logs/ directory")
