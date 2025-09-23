#!/usr/bin/env python3
"""
Enhanced logging demo for SAP OData Connector
Logs to both file and terminal with detailed analysis
"""

import sys
import asyncio
import structlog
import logging
from datetime import datetime
from pathlib import Path

# Add the odc directory to Python path
sys.path.append('./odc')

def setup_enhanced_logging():
    """Setup comprehensive logging to both file and console"""
    
    # Create logs directory
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"odata_analysis_{timestamp}.log"
    
    # Configure Python's standard logging for file output
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
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
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False)  # No colors for file
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG level
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return str(log_file)

def analyze_config_parameters():
    """Analyze and explain ClientConfig parameters"""
    
    log_file = setup_enhanced_logging()
    logger = structlog.get_logger("config_analyzer")
    
    logger.info("=== SAP OData Connector Configuration Analysis ===", log_file=log_file)
    
    # Parameter explanations
    parameters = {
        "batch_size": {
            "description": "Records per OData API call ($top parameter)",
            "default": 1000,
            "impact": "Larger = fewer API calls, more memory per request",
            "example": "batch_size=50 → Products?$top=50&$skip=0"
        },
        "total_records_limit": {
            "description": "GLOBAL limit across ALL entities (not per-entity)",
            "default": "None (unlimited)",
            "impact": "Stops entire connector when limit reached",
            "example": "total_records_limit=100 → stops after 100 total records"
        },
        "max_workers": {
            "description": "Number of concurrent HTTP workers",
            "default": 5,
            "impact": "More workers = faster processing, higher server load",
            "coordination": "All workers share rate limit and total_records_limit"
        },
        "requests_per_second": {
            "description": "Global rate limit using token bucket algorithm",
            "default": 5.0,
            "impact": "Higher rate = faster processing, may hit server limits",
            "sharing": "All workers compete for tokens from same bucket"
        }
    }
    
    for param, details in parameters.items():
        logger.info(f"Parameter: {param}",
                   description=details["description"],
                   default=details["default"],
                   impact=details["impact"])
        
        if "example" in details:
            logger.info(f"Example for {param}", example=details["example"])
        
        if "coordination" in details:
            logger.info(f"Coordination for {param}", coordination=details["coordination"])
    
    # Race condition analysis
    logger.warning("=== IDENTIFIED RACE CONDITIONS ===")
    
    race_conditions = [
        {
            "issue": "Total Records Limit Race",
            "description": "Multiple workers check limit simultaneously",
            "consequence": "May fetch more records than limit allows",
            "code_location": "connector.py - total_processed >= config.total_records_limit"
        },
        {
            "issue": "Pagination Coordination",
            "description": "Workers may start next page before previous completes",
            "consequence": "Records may be skipped or double-counted",
            "solution": "Better synchronization between workers"
        },
        {
            "issue": "Rate Limiting Effects",
            "description": "Delayed requests complete after limit reached",
            "consequence": "Inconsistent record counts across runs",
            "mitigation": "Lower requests_per_second with more workers"
        }
    ]
    
    for condition in race_conditions:
        logger.warning("Race condition detected",
                      issue=condition["issue"],
                      description=condition["description"],
                      consequence=condition["consequence"])
        
        if "solution" in condition:
            logger.info("Suggested solution", solution=condition["solution"])
        if "mitigation" in condition:
            logger.info("Mitigation strategy", mitigation=condition["mitigation"])
    
    # Configuration recommendations
    logger.info("=== CONFIGURATION RECOMMENDATIONS ===")
    
    recommendations = [
        {
            "scenario": "High Volume, Stable Server",
            "config": {
                "batch_size": 1000,
                "max_workers": 10,
                "requests_per_second": 20.0,
                "total_records_limit": None
            },
            "rationale": "Maximize throughput with large batches and many workers"
        },
        {
            "scenario": "Rate-Limited Server",
            "config": {
                "batch_size": 100,
                "max_workers": 3,
                "requests_per_second": 2.0,
                "total_records_limit": None
            },
            "rationale": "Respect server limits with conservative settings"
        },
        {
            "scenario": "Testing/Development",
            "config": {
                "batch_size": 50,
                "max_workers": 2,
                "requests_per_second": 1.0,
                "total_records_limit": 200
            },
            "rationale": "Small batches for debugging, limited records for quick tests"
        }
    ]
    
    for rec in recommendations:
        logger.info("Configuration recommendation",
                   scenario=rec["scenario"],
                   config=rec["config"],
                   rationale=rec["rationale"])
    
    logger.info("Analysis complete. Check log file for full details", log_file=log_file)
    
    return log_file

if __name__ == "__main__":
    log_file = analyze_config_parameters()
    print(f"\nDetailed analysis saved to: {log_file}")
    print("\nKey Findings:")
    print("1. total_records_limit is GLOBAL across all entities, not per-entity")
    print("2. Race conditions between workers cause inconsistent record counts")
    print("3. Higher worker counts with rate limiting can cause coordination issues")
    print("4. File logging is now active - check logs/ directory for detailed output")
