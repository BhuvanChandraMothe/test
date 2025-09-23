#!/usr/bin/env python3
"""Debug script to test Northwind service connection"""

import asyncio
import httpx
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_northwind_connection():
    """Test basic connection to Northwind service"""
    
    print("🔍 Testing Northwind service connection...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test metadata endpoint
            print("📋 Fetching metadata...")
            metadata_response = await client.get('https://services.odata.org/V4/Northwind/Northwind.svc/$metadata')
            print(f"Metadata Status: {metadata_response.status_code}")
            print(f"Metadata Content Length: {len(metadata_response.text)}")
            print(f"First 200 chars: {metadata_response.text[:200]}")
            
            # Test a simple entity set
            print("\n📊 Testing entity set access...")
            customers_response = await client.get('https://services.odata.org/V4/Northwind/Northwind.svc/Customers?$top=1')
            print(f"Customers Status: {customers_response.status_code}")
            print(f"Customers Content: {customers_response.text[:300]}")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_northwind_connection())
    sys.exit(0 if success else 1)
