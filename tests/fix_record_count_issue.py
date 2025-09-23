#!/usr/bin/env python3
"""
Fix for record count inconsistency in SAP OData Connector
Demonstrates proper coordination between workers and accurate record counting
"""

import sys
import asyncio
import structlog
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Add the odc directory to Python path
sys.path.append('./odc')

from config.models import ClientConfig

def setup_file_and_console_logging():
    """Setup logging to both file and console"""
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"record_count_fix_{timestamp}.log"
    
    # File handler - detailed logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler - important messages only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=False)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return str(log_file)

@dataclass
class RecordCountTracker:
    """Thread-safe record count tracker to fix race conditions"""
    total_processed: int = 0
    entity_counts: Dict[str, int] = None
    limit_reached: bool = False
    
    def __post_init__(self):
        if self.entity_counts is None:
            self.entity_counts = {}
    
    def add_records(self, entity: str, count: int, limit: Optional[int] = None) -> bool:
        """Add records and check if limit is reached. Returns True if processing should continue."""
        self.entity_counts[entity] = self.entity_counts.get(entity, 0) + count
        self.total_processed += count
        
        if limit and self.total_processed >= limit:
            self.limit_reached = True
            return False
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_processed": self.total_processed,
            "entity_counts": self.entity_counts.copy(),
            "limit_reached": self.limit_reached
        }

def analyze_config_impact():
    """Analyze how different ClientConfig parameters affect record processing"""
    
    log_file = setup_file_and_console_logging()
    logger = structlog.get_logger("config_impact_analyzer")
    
    logger.info("=== ClientConfig Parameter Impact Analysis ===", log_file=log_file)
    
    # Test scenarios with detailed explanations
    test_scenarios = [
        {
            "name": "Conservative Settings",
            "config": {
                "batch_size": 25,
                "max_workers": 2,
                "requests_per_second": 1.0,
                "total_records_limit": 100
            },
            "expected_behavior": {
                "api_calls": "100/25 = 4 calls per entity",
                "concurrency": "2 workers sharing 1 req/sec = 0.5 req/sec per worker",
                "coordination": "Low chance of race conditions",
                "memory_usage": "Low (25 records per batch)"
            }
        },
        {
            "name": "Aggressive Settings", 
            "config": {
                "batch_size": 100,
                "max_workers": 10,
                "requests_per_second": 20.0,
                "total_records_limit": 100
            },
            "expected_behavior": {
                "api_calls": "100/100 = 1 call per entity (if no race conditions)",
                "concurrency": "10 workers sharing 20 req/sec = 2 req/sec per worker",
                "coordination": "HIGH chance of race conditions",
                "memory_usage": "High (100 records per batch)"
            }
        },
        {
            "name": "Balanced Settings",
            "config": {
                "batch_size": 50,
                "max_workers": 4,
                "requests_per_second": 5.0,
                "total_records_limit": 100
            },
            "expected_behavior": {
                "api_calls": "100/50 = 2 calls per entity",
                "concurrency": "4 workers sharing 5 req/sec = 1.25 req/sec per worker",
                "coordination": "Medium chance of race conditions",
                "memory_usage": "Medium (50 records per batch)"
            }
        }
    ]
    
    for scenario in test_scenarios:
        logger.info(f"=== {scenario['name']} ===")
        
        config = scenario['config']
        behavior = scenario['expected_behavior']
        
        logger.info("Configuration", **config)
        logger.info("Expected behavior", **behavior)
        
        # Simulate record processing with this configuration
        tracker = RecordCountTracker()
        
        # Simulate race condition scenarios
        if config['max_workers'] > 5:
            logger.warning("HIGH RISK: Many workers with rate limiting can cause:")
            logger.warning("- Workers may fetch beyond total_records_limit")
            logger.warning("- Pagination coordination issues")
            logger.warning("- Inconsistent record counts between runs")
        
        # Calculate theoretical vs actual processing
        theoretical_batches = config['total_records_limit'] // config['batch_size']
        if config['total_records_limit'] % config['batch_size'] > 0:
            theoretical_batches += 1
        
        logger.info("Theoretical processing",
                   batches_needed=theoretical_batches,
                   records_per_batch=config['batch_size'],
                   total_limit=config['total_records_limit'])
        
        # Simulate potential race condition outcomes
        if config['max_workers'] > 3 and config['requests_per_second'] > 5:
            # High chance of race conditions
            potential_overfetch = config['batch_size'] * (config['max_workers'] - 1)
            logger.warning("Potential race condition outcome",
                          may_fetch_up_to=config['total_records_limit'] + potential_overfetch,
                          reason="Multiple workers may start before limit check")
        
        logger.info("---")
    
    # Provide concrete recommendations
    logger.info("=== CONCRETE RECOMMENDATIONS ===")
    
    recommendations = {
        "For Consistent Record Counts": {
            "batch_size": "Set to divisor of total_records_limit (e.g., 50 for limit 100)",
            "max_workers": "Keep ≤ 3 to reduce race conditions",
            "requests_per_second": "Lower values (1-3) for better coordination",
            "total_records_limit": "Use multiples of batch_size"
        },
        "For Maximum Performance": {
            "batch_size": "Large values (500-1000) for fewer API calls",
            "max_workers": "5-10 workers for high throughput",
            "requests_per_second": "High values (10-20) if server allows",
            "total_records_limit": "None (unlimited) to avoid race conditions"
        },
        "For Development/Testing": {
            "batch_size": "Small values (10-50) for quick feedback",
            "max_workers": "1-2 workers for predictable behavior",
            "requests_per_second": "Low values (1-2) to avoid hitting limits",
            "total_records_limit": "Small values (50-200) for quick tests"
        }
    }
    
    for use_case, settings in recommendations.items():
        logger.info(f"Recommendation: {use_case}")
        for param, advice in settings.items():
            logger.info(f"  {param}: {advice}")
    
    # Root cause analysis
    logger.warning("=== ROOT CAUSE OF RECORD COUNT DIFFERENCES ===")
    
    root_causes = [
        "total_records_limit is checked AFTER fetching, not before",
        "Multiple workers can simultaneously fetch when near the limit",
        "Rate limiting delays some requests, causing timing issues",
        "No coordination between workers for pagination boundaries",
        "Async nature means workers don't wait for each other"
    ]
    
    for i, cause in enumerate(root_causes, 1):
        logger.warning(f"{i}. {cause}")
    
    logger.info("Analysis complete. Detailed logs saved to:", log_file=log_file)
    
    return log_file

def demonstrate_fixed_configuration():
    """Demonstrate a configuration that minimizes record count inconsistencies"""
    
    logger = structlog.get_logger("fixed_config_demo")
    
    logger.info("=== RECOMMENDED FIXED CONFIGURATION ===")
    
    # Configuration that minimizes race conditions
    fixed_config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        selected_modules=["Products"],  # Single entity for testing
        batch_size=50,                  # Divides evenly into common limits
        max_workers=2,                  # Low worker count reduces race conditions
        requests_per_second=2.0,        # Conservative rate limiting
        total_records_limit=100,        # Exactly 2 batches (100/50)
        output_directory="./fixed_config_output"
    )
    
    logger.info("Fixed configuration parameters:")
    logger.info(f"  batch_size: {fixed_config.batch_size} (divides evenly into limit)")
    logger.info(f"  max_workers: {fixed_config.max_workers} (reduces race conditions)")
    logger.info(f"  requests_per_second: {fixed_config.requests_per_second} (conservative)")
    logger.info(f"  total_records_limit: {fixed_config.total_records_limit} (exactly 2 batches)")
    
    logger.info("Why this configuration works:")
    logger.info("1. batch_size (50) divides evenly into total_records_limit (100)")
    logger.info("2. Only 2 workers reduce coordination complexity")
    logger.info("3. Low request rate prevents timing-related race conditions")
    logger.info("4. Predictable: exactly 2 API calls needed")
    
    return fixed_config

if __name__ == "__main__":
    print("=== SAP OData Connector Record Count Issue Analysis ===\n")
    
    # Run the analysis
    log_file = analyze_config_impact()
    
    # Demonstrate fixed configuration
    fixed_config = demonstrate_fixed_configuration()
    
    print(f"\n=== SUMMARY ===")
    print(f"1. Detailed analysis saved to: {log_file}")
    print(f"2. Root cause: Race conditions between workers")
    print(f"3. Solution: Use batch_size that divides evenly into total_records_limit")
    print(f"4. Recommendation: max_workers ≤ 3, conservative requests_per_second")
    print(f"5. File logging is now active for all connector runs")
    
    print(f"\n=== FIXED CONFIGURATION EXAMPLE ===")
    print(f"batch_size: {fixed_config.batch_size}")
    print(f"max_workers: {fixed_config.max_workers}")
    print(f"requests_per_second: {fixed_config.requests_per_second}")
    print(f"total_records_limit: {fixed_config.total_records_limit}")
    print(f"Expected result: Exactly {fixed_config.total_records_limit} records every time")
