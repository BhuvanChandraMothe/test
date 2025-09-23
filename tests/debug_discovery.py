#!/usr/bin/env python3
"""Debug discovery phase integration"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "odc"))

from config.models import ClientConfig
from connector import SAPODataConnector

async def debug_discovery_integration():
    """Debug the discovery phase step by step"""
    
    print("🔍 Debugging discovery phase integration...")
    
    config = ClientConfig(
        odata_service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        username=None,
        password=None,
        selected_modules=[],
        total_records_limit=50,
        batch_size=10,
        max_workers=1,
        requests_per_second=1.0,
        output_directory="./debug_output",
        raw_data_directory="./debug_output/raw",
        processed_data_directory="./debug_output/processed"
    )
    
    connector = SAPODataConnector(config)
    
    try:
        print("🚀 Initializing connector...")
        await connector.initialize()
        
        print("\n📋 Testing metadata service...")
        async with connector.metadata_service:
            entity_schemas = await connector.metadata_service.fetch_metadata()
            print(f"Entity schemas found: {len(entity_schemas)}")
            entity_names = list(entity_schemas.keys())[:5]
            print(f"First 5 entities: {entity_names}")
        
        print(f"\n📊 Testing count service with entities: {entity_names}")
        async with connector.count_service:
            entity_counts = await connector.count_service.get_entity_counts(entity_names)
            print(f"Entity counts: {entity_counts}")
            total_records = sum(entity_counts.values())
            print(f"Total records: {total_records}")
        
        print(f"\n🔧 Testing plan generation...")
        # Simulate what happens in discovery phase
        processing_order = [entity_names]  # Simple single-level processing
        connector.plan_generator.create_execution_plan(
            entity_counts, processing_order, None
        )
        
        initial_commands = connector.plan_generator.get_initial_commands()
        print(f"Initial commands generated: {len(initial_commands)}")
        
        if initial_commands:
            print("Sample commands:")
            for i, cmd in enumerate(initial_commands[:3]):
                print(f"  {i+1}. {cmd.command_type.value} - {cmd.entity_set} (skip={cmd.skip}, top={cmd.top})")
        else:
            print("❌ No commands generated!")
            print("Entity plans:", len(connector.plan_generator.entity_plans))
            for name, plan in connector.plan_generator.entity_plans.items():
                print(f"  {name}: {plan.total_records} records, {len(plan.commands)} commands")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_discovery_integration())
    sys.exit(0 if success else 1)
