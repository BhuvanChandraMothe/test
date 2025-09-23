#!/usr/bin/env python3
"""Test count endpoint directly"""

import asyncio
import httpx

async def test_count():
    async with httpx.AsyncClient() as client:
        # Test Categories count
        r = await client.get('https://services.odata.org/V4/Northwind/Northwind.svc/Categories/$count')
        print(f'Categories count - Status: {r.status_code}, Content: {r.text}')
        
        # Test Categories data
        r2 = await client.get('https://services.odata.org/V4/Northwind/Northwind.svc/Categories?$top=1')
        print(f'Categories data - Status: {r2.status_code}, Content length: {len(r2.text)}')

if __name__ == "__main__":
    asyncio.run(test_count())
