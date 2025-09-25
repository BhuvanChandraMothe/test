#!/usr/bin/env python3
"""
Check the status of the last run and display available metrics/output files
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_output_files():
    """Check what output files were created"""
    output_dir = Path("./test_output")
    
    if not output_dir.exists():
        print("❌ No output directory found. The connector may not have run yet.")
        return False
    
    print("📁 Output Directory Analysis:")
    print("=" * 50)
    
    # Check raw data
    raw_dir = output_dir / "raw"
    if raw_dir.exists():
        raw_files = list(raw_dir.rglob("*.json"))
        print(f"📄 Raw Data Files: {len(raw_files)}")
        total_raw_size = sum(f.stat().st_size for f in raw_files)
        print(f"   Total Size: {total_raw_size:,} bytes")
        
        # Show some examples
        for i, file_path in enumerate(raw_files[:5]):
            rel_path = file_path.relative_to(output_dir)
            size = file_path.stat().st_size
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"   - {rel_path} ({size:,} bytes, {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        if len(raw_files) > 5:
            print(f"   ... and {len(raw_files) - 5} more files")
    
    # Check processed data
    processed_dir = output_dir / "processed"
    if processed_dir.exists():
        processed_files = list(processed_dir.rglob("*.json"))
        print(f"\n🔄 Processed Data Files: {len(processed_files)}")
        total_processed_size = sum(f.stat().st_size for f in processed_files)
        print(f"   Total Size: {total_processed_size:,} bytes")
        
        # Analyze each entity
        entities_processed = {}
        for file_path in processed_files:
            entity_name = file_path.parent.name
            if entity_name not in entities_processed:
                entities_processed[entity_name] = []
            entities_processed[entity_name].append(file_path)
        
        print(f"\n📊 Entities Processed: {len(entities_processed)}")
        for entity_name, files in entities_processed.items():
            total_size = sum(f.stat().st_size for f in files)
            print(f"   - {entity_name}: {len(files)} files, {total_size:,} bytes")
            
            # Try to count records in the main file
            main_file = next((f for f in files if f.name == f"{entity_name}.json"), None)
            if main_file and main_file.exists():
                try:
                    with open(main_file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            print(f"     Records: {len(data)}")
                        elif isinstance(data, dict) and 'records' in data:
                            print(f"     Records: {len(data['records'])}")
                except Exception as e:
                    print(f"     Records: Unable to count ({e})")
    
    # Check for metadata files
    metadata_files = list(output_dir.glob("*.xml")) + list(output_dir.glob("*.json"))
    if metadata_files:
        print(f"\n📋 Metadata Files: {len(metadata_files)}")
        for file_path in metadata_files:
            size = file_path.stat().st_size
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"   - {file_path.name} ({size:,} bytes, {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    return True

def check_metrics():
    """Check available metrics"""
    try:
        from odc.monitoring.metrics import get_metrics_collector
        
        print("\n📈 Current Metrics:")
        print("=" * 50)
        
        metrics = get_metrics_collector()
        prometheus_text = metrics.get_metrics_text()
        
        if prometheus_text:
            # Parse and display key metrics
            lines = prometheus_text.strip().split('\n')
            for line in lines:
                if line.startswith('#') or not line.strip():
                    continue
                print(f"   {line}")
        else:
            print("   No metrics available")
            
    except Exception as e:
        print(f"\n⚠️ Could not retrieve metrics: {e}")

def main():
    """Main status check"""
    print("🔍 SAP OData Connector - Status Check")
    print("=" * 60)
    
    # Check if connector is currently running
    print("🔄 Checking for running processes...")
    # This is a simple check - in a real scenario you might check for process IDs
    
    # Check output files
    has_output = check_output_files()
    
    # Check metrics
    check_metrics()
    
    if has_output:
        print("\n✅ Previous run detected with output files")
        print("   Use the improved test script to run again with better stats display")
    else:
        print("\n❌ No previous run detected")
        print("   Run the connector to generate output")
    
    print("\n💡 Recommendations:")
    print("   1. Use 'python test_northwind_improved.py' for better stats display")
    print("   2. Check the ./test_output directory for detailed results")
    print("   3. Monitor the terminal output during execution")

if __name__ == "__main__":
    main()
