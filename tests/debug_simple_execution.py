#!/usr/bin/env python3
"""Simple execution test bypassing resilience patterns"""

import asyncio
import sys
import httpx
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent / "odc"))

from config.models import ODataConfig
from planning.plan_generator import FetchCommand, CommandType, Priority

async def test_simple_execution():
    """Test direct HTTP execution without resilience patterns"""
    
    print("🔍 Testing simple HTTP execution...")
    
    config = ODataConfig(service_url="https://services.odata.org/V4/Northwind/Northwind.svc")
    
    # Create a simple fetch command
    command = FetchCommand(
        command_id="test_categories",
        command_type=CommandType.FETCH_PAGE,
        entity_set="Categories",
        skip=0,
        top=5
    )
    
    print(f"Testing command: {command.entity_set} (skip={command.skip}, top={command.top})")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build URL
            url = config.entity_set_url(command.entity_set)
            if command.url_params:
                url += f"?{urlencode(command.url_params)}"
            
            print(f"Request URL: {url}")
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Make request
            response = await client.get(url, headers=headers)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response data keys: {list(data.keys())}")
                
                if 'value' in data:
                    records = data['value']
                    print(f"Records found: {len(records)}")
                    if records:
                        print(f"First record keys: {list(records[0].keys())}")
                        print(f"Sample record: {records[0]}")
                else:
                    print("No 'value' key in response")
                    print(f"Response content: {response.text[:500]}")
            else:
                print(f"Error response: {response.text}")
            
            return response.status_code == 200
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_execution())
    sys.exit(0 if success else 1)
