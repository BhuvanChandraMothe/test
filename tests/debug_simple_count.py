#!/usr/bin/env python3
"""Simple debug for count service"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "odc"))

from config.models import ODataConfig
from services.count import CountService

async def test_simple_count():
    config = ODataConfig(service_url="https://services.odata.org/V4/Northwind/Northwind.svc")
    
    async with CountService(config) as count_service:
        # Test single entity count
        print("Testing Categories count...")
        try:
            count = await count_service._get_single_entity_count("Categories")
            print(f"Categories count: {count}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_count())
