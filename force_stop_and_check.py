#!/usr/bin/env python3
"""
Force stop any hanging processes and check results
"""

import os
import sys
import psutil
import signal
from pathlib import Path
import json
from datetime import datetime

def find_and_kill_python_processes():
    """Find and kill any hanging Python processes related to the connector"""
    killed_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any('test_northwind' in arg or 'odc' in arg for arg in cmdline):
                    print(f"Found hanging process: PID {proc.info['pid']}, CMD: {' '.join(cmdline)}")
                    proc.terminate()  # Try graceful termination first
                    killed_processes.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_processes:
        print(f"Terminated {len(killed_processes)} processes: {killed_processes}")
        # Wait a bit for graceful termination
        import time
        time.sleep(2)
        
        # Force kill if still running
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['pid'] in killed_processes and proc.is_running():
                    print(f"Force killing PID {proc.info['pid']}")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    else:
        print("No hanging Python processes found")

def check_results():
    """Check what results were produced"""
    output_dir = Path("./test_output")
    
    if not output_dir.exists():
        print("❌ No output directory found")
        return
    
    print("\n📊 Results Analysis:")
    print("=" * 50)
    
    # Check processed data
    processed_dir = output_dir / "processed"
    if processed_dir.exists():
        entities = {}
        total_records = 0
        
        for entity_dir in processed_dir.iterdir():
            if entity_dir.is_dir():
                entity_name = entity_dir.name
                main_file = entity_dir / f"{entity_name}.json"
                
                if main_file.exists():
                    try:
                        with open(main_file, 'r') as f:
                            data = json.load(f)
                            record_count = len(data) if isinstance(data, list) else 0
                            entities[entity_name] = record_count
                            total_records += record_count
                    except Exception as e:
                        entities[entity_name] = f"Error: {e}"
        
        print(f"📈 Entities processed: {len(entities)}")
        print(f"📊 Total records: {total_records}")
        print("\nEntity breakdown:")
        for entity, count in sorted(entities.items()):
            print(f"   - {entity}: {count}")
    
    # Check raw data
    raw_dir = output_dir / "raw"
    if raw_dir.exists():
        raw_files = list(raw_dir.rglob("*.json"))
        total_size = sum(f.stat().st_size for f in raw_files)
        print(f"\n📄 Raw files: {len(raw_files)}")
        print(f"💾 Total raw data size: {total_size:,} bytes")

def main():
    """Main function"""
    print("🛑 Force Stop and Check Results")
    print("=" * 60)
    
    # Kill hanging processes
    find_and_kill_python_processes()
    
    # Check results
    check_results()
    
    print("\n💡 Next steps:")
    print("   1. The hanging issue has been fixed in the connector code")
    print("   2. Use 'python test_with_timeout.py' for a clean test with timeout protection")
    print("   3. The new version will not hang and will show proper completion stats")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        # Fallback - just check results without killing processes
        try:
            check_results()
        except Exception as e2:
            print(f"Could not check results: {e2}")
