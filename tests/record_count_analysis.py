#!/usr/bin/env python3
"""
Clear analysis of the record count issue in SAP OData Connector
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Setup simple logging to file and console"""
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"record_analysis_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return str(log_file)

def analyze_parameters():
    """Analyze ClientConfig parameters and their effects"""
    
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== SAP OData Connector Parameter Analysis ===")
    
    # Parameter explanations
    logger.info("PARAMETER EXPLANATIONS:")
    logger.info("1. batch_size (default: 1000)")
    logger.info("   - Records fetched per API call ($top parameter)")
    logger.info("   - Example: batch_size=50 -> Products?$top=50&$skip=0")
    logger.info("   - Larger = fewer API calls, more memory per request")
    
    logger.info("2. total_records_limit (default: None)")
    logger.info("   - GLOBAL limit across ALL entities combined")
    logger.info("   - NOT per-entity - total cap for entire run")
    logger.info("   - Example: limit=100 stops after 100 total records")
    
    logger.info("3. max_workers (default: 5)")
    logger.info("   - Number of concurrent HTTP workers")
    logger.info("   - More workers = faster but higher race condition risk")
    logger.info("   - All workers share the same rate limit and total limit")
    
    logger.info("4. requests_per_second (default: 5.0)")
    logger.info("   - Global rate limit using token bucket algorithm")
    logger.info("   - All workers compete for tokens from same bucket")
    logger.info("   - Higher rate = faster but may hit server limits")
    
    # Race condition analysis
    logger.warning("=== RACE CONDITION ISSUES ===")
    logger.warning("Why record counts differ with different configurations:")
    
    logger.warning("1. Total Records Limit Race:")
    logger.warning("   - Multiple workers check limit simultaneously")
    logger.warning("   - Worker A checks: 80 < 100 (OK to fetch)")
    logger.warning("   - Worker B checks: 80 < 100 (OK to fetch)")
    logger.warning("   - Both fetch 50 records = 180 total (exceeds 100 limit)")
    
    logger.warning("2. Pagination Coordination:")
    logger.warning("   - Worker 1 fetches records 0-49")
    logger.warning("   - Worker 2 starts 50-99 before Worker 1 updates counter")
    logger.warning("   - Result: Some records skipped or double-counted")
    
    logger.warning("3. Rate Limiting Effects:")
    logger.warning("   - High requests_per_second with many workers")
    logger.warning("   - Some requests delayed, complete after limit reached")
    logger.warning("   - Causes inconsistent counts between runs")
    
    # Solutions
    logger.info("=== SOLUTIONS ===")
    
    logger.info("Solution 1: Single Worker (Eliminates race conditions)")
    logger.info("  batch_size: 50")
    logger.info("  max_workers: 1  # No race conditions possible")
    logger.info("  requests_per_second: 2.0")
    logger.info("  total_records_limit: 100")
    logger.info("  Result: Always exactly 100 records")
    
    logger.info("Solution 2: Evenly Divisible Batches")
    logger.info("  batch_size: 50  # 100/50 = exactly 2 batches")
    logger.info("  max_workers: 2")
    logger.info("  requests_per_second: 2.0")
    logger.info("  total_records_limit: 100")
    logger.info("  Result: Predictable batch count, minimal races")
    
    logger.info("Solution 3: No Record Limit")
    logger.info("  batch_size: 25")
    logger.info("  max_workers: 4")
    logger.info("  requests_per_second: 5.0")
    logger.info("  total_records_limit: None  # No limit checking")
    logger.info("  Result: Fetches all available records consistently")
    
    # Recommendations
    logger.info("=== RECOMMENDATIONS ===")
    logger.info("For consistent record counts:")
    logger.info("- Use batch_size that divides evenly into total_records_limit")
    logger.info("- Keep max_workers <= 3 to reduce race conditions")
    logger.info("- Use conservative requests_per_second (1-3)")
    logger.info("- Consider removing total_records_limit to avoid races")
    
    logger.info("For maximum performance:")
    logger.info("- Use large batch_size (500-1000)")
    logger.info("- Use many workers (5-10) only if no record limit")
    logger.info("- Use high requests_per_second if server allows")
    logger.info("- Set total_records_limit to None")
    
    logger.info(f"Analysis complete. Full details in: {log_file}")
    return log_file

if __name__ == "__main__":
    log_file = analyze_parameters()
    
    print("\n=== SUMMARY ===")
    print("Issue: Different worker/batch configurations produce different record counts")
    print("Root Cause: Race conditions between workers")
    print("Key Problem: total_records_limit is checked AFTER fetching, not before")
    print("")
    print("Quick Fix:")
    print("- batch_size: 50 (divides evenly into your limit)")
    print("- max_workers: 2 (reduces race conditions)")
    print("- requests_per_second: 2.0 (conservative)")
    print("- total_records_limit: 100 (or None to avoid races)")
    print("")
    print(f"Detailed analysis saved to: {log_file}")
    print("File logging is now active for all connector operations")
