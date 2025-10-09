"""
Command-line interface for SAP OData Connector
"""
import asyncio
import click
import json
from pathlib import Path
from typing import Optional
import sys

from .connector import SAPODataConnector
from .config.models import ClientConfig


@click.group()
@click.version_option(version='1.0.2')
def main():
    """SAP OData Connector - Extract data from SAP OData services
    
    Examples:
        # Fetch all entities from a service
        sap-odata-connector fetch --url https://services.odata.org/V4/Northwind/Northwind.svc/
        
        # Fetch specific entity with filter
        sap-odata-connector fetch --url https://your-service.com/ --entity Products --filter "Price gt 100"
        
        # Use SAP module mapping
        sap-odata-connector fetch --server sapes5.sapdevcenter.com --module ES5 --user username --password pass
    """
    pass


@main.command()
@click.option('--url', '-u', help='Full OData service URL')
@click.option('--server', '-s', help='SAP server hostname')
@click.option('--port', '-p', type=int, default=443, help='SAP server port (default: 443)')
@click.option('--module', '-m', help='SAP module name (e.g., ES5, FI, MM)')
@click.option('--service', help='OData service name (alternative to module)')
@click.option('--user', help='Username for authentication')
@click.option('--password', help='Password for authentication')
@click.option('--entity', '-e', help='Specific entity to fetch (e.g., Products)')
@click.option('--entities', help='Comma-separated list of entities to fetch')
@click.option('--filter', '-f', help='OData $filter condition')
@click.option('--select', help='OData $select fields (comma-separated)')
@click.option('--expand', help='OData $expand relations (comma-separated)')
@click.option('--orderby', help='OData $orderby clause')
@click.option('--limit', '-l', type=int, help='Maximum records to fetch')
@click.option('--batch-size', type=int, default=1000, help='Records per batch (default: 1000)')
@click.option('--output', '-o', default='./output', help='Output directory (default: ./output)')
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Output format')
@click.option('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')
@click.option('--timeout', type=int, default=60, help='Request timeout in seconds (default: 60)')
def fetch(**kwargs):
    """Fetch data from OData service
    
    Examples:
        # Fetch all data from Northwind V4
        sap-odata-connector fetch --url https://services.odata.org/V4/Northwind/Northwind.svc/
        
        # Fetch specific entity with filter
        sap-odata-connector fetch --url https://your-service.com/ --entity Products --filter "Price gt 100" --limit 50
        
        # Use SAP credentials
        sap-odata-connector fetch --server sapes5.sapdevcenter.com --module ES5 --user P2010682507 --password yourpass
    """
    asyncio.run(_fetch_async(**kwargs))


async def _fetch_async(**kwargs):
    """Async implementation of fetch command"""
    try:
        # Build configuration
        config = _build_config(**kwargs)
        
        click.echo(f"\n{'='*70}")
        click.echo("SAP OData Connector - Data Extraction")
        click.echo(f"{'='*70}")
        click.echo(f"Service URL: {config.service_url}")
        click.echo(f"Output Directory: {config.output_directory}")
        
        # Initialize connector
        click.echo("\n[1/4] Initializing connector...")
        connector = SAPODataConnector(config)
        
        try:
            info = await connector.initialize()
            click.echo(f"✓ Connected successfully!")
            click.echo(f"  - Total entities available: {info['total_entities']}")
            click.echo(f"  - Total records: {info['total_records']:,}")
            
            # Determine what to fetch
            entity_name = kwargs.get('entity')
            entities_list = kwargs.get('entities')
            selected_entities = entities_list.split(',') if entities_list else None
            
            # Build query options
            query_options = {
                'filter_condition': kwargs.get('filter'),
                'select_fields': kwargs.get('select'),
                'expand_relations': kwargs.get('expand'),
                'order_by': kwargs.get('orderby'),
                'record_limit': kwargs.get('limit'),
                'batch_size': kwargs.get('batch_size', 1000),
                'max_workers': kwargs.get('workers', 5)
            }
            
            # Remove None values
            query_options = {k: v for k, v in query_options.items() if v is not None}
            
            click.echo("\n[2/4] Fetching data...")
            if entity_name:
                click.echo(f"  - Entity: {entity_name}")
            elif selected_entities:
                click.echo(f"  - Entities: {', '.join(selected_entities)}")
            else:
                click.echo(f"  - Mode: All entities")
            
            if query_options.get('filter_condition'):
                click.echo(f"  - Filter: {query_options['filter_condition']}")
            if query_options.get('record_limit'):
                click.echo(f"  - Limit: {query_options['record_limit']} records")
            
            # Fetch data
            result = await connector.get_data(
                entity_name=entity_name,
                selected_entities=selected_entities,
                **query_options
            )
            
            # Display results
            stats = result['execution_stats']
            click.echo("\n[3/4] Data fetched successfully!")
            click.echo(f"  - Records processed: {stats['records_processed']:,}")
            click.echo(f"  - Entities processed: {stats.get('entities_processed', 1)}")
            click.echo(f"  - Duration: {stats['duration_seconds']:.2f} seconds")
            if stats['duration_seconds'] > 0:
                rate = stats['records_processed'] / stats['duration_seconds']
                click.echo(f"  - Rate: {rate:.0f} records/second")
            
            click.echo("\n[4/4] Saving results...")
            click.echo(f"  - Output directory: {config.output_directory}")
            
            # Check for query results
            query_results_dir = Path(config.output_directory) / "query_results"
            if query_results_dir.exists():
                files = list(query_results_dir.glob("*.json"))
                if files:
                    click.echo(f"  - Query results: {len(files)} file(s)")
                    for f in files[:3]:  # Show first 3
                        click.echo(f"    • {f.name}")
                    if len(files) > 3:
                        click.echo(f"    ... and {len(files) - 3} more")
            
            # Check for processed data
            processed_dir = Path(config.output_directory) / "processed"
            if processed_dir.exists():
                entity_dirs = [d for d in processed_dir.iterdir() if d.is_dir()]
                if entity_dirs:
                    click.echo(f"  - Processed data: {len(entity_dirs)} entity folder(s)")
                    for d in entity_dirs[:3]:
                        click.echo(f"    • {d.name}/")
                    if len(entity_dirs) > 3:
                        click.echo(f"    ... and {len(entity_dirs) - 3} more")
            
            click.echo(f"\n{'='*70}")
            click.echo("✅ SUCCESS! Data extraction completed")
            click.echo(f"{'='*70}\n")
            
        finally:
            await connector.cleanup()
            
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option('--url', '-u', help='Full OData service URL')
@click.option('--server', '-s', help='SAP server hostname')
@click.option('--port', '-p', type=int, default=443, help='SAP server port')
@click.option('--module', '-m', help='SAP module name')
@click.option('--user', help='Username for authentication')
@click.option('--password', help='Password for authentication')
def list_entities(**kwargs):
    """List all available entities in the OData service
    
    Example:
        sap-odata-connector list-entities --url https://services.odata.org/V4/Northwind/Northwind.svc/
    """
    asyncio.run(_list_entities_async(**kwargs))


async def _list_entities_async(**kwargs):
    """Async implementation of list-entities command"""
    try:
        config = _build_config(**kwargs)
        
        click.echo(f"\n{'='*70}")
        click.echo("Available Entities")
        click.echo(f"{'='*70}")
        click.echo(f"Service: {config.service_url}\n")
        
        connector = SAPODataConnector(config)
        
        try:
            info = await connector.initialize()
            
            click.echo(f"Total Entities: {info['total_entities']}")
            click.echo(f"Total Records: {info['total_records']:,}\n")
            
            # Display entities in a table format
            click.echo(f"{'Entity Name':<30} {'Records':<15} {'Properties':<15}")
            click.echo("-" * 70)
            
            for entity in info['entities']:
                name = entity['name']
                count = entity['record_count']
                props = entity['total_properties']
                click.echo(f"{name:<30} {count:>10,}     {props:>10}")
            
            click.echo(f"\n{'='*70}\n")
            
        finally:
            await connector.cleanup()
            
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--url', '-u', help='Full OData service URL')
@click.option('--server', '-s', help='SAP server hostname')
@click.option('--port', '-p', type=int, default=443, help='SAP server port')
@click.option('--module', '-m', help='SAP module name')
@click.option('--user', help='Username for authentication')
@click.option('--password', help='Password for authentication')
@click.option('--output', '-o', default='./metadata.json', help='Output file (default: ./metadata.json)')
def metadata(**kwargs):
    """Export service metadata to JSON file
    
    Example:
        sap-odata-connector metadata --url https://services.odata.org/V4/Northwind/Northwind.svc/ -o northwind_metadata.json
    """
    asyncio.run(_metadata_async(**kwargs))


async def _metadata_async(**kwargs):
    """Async implementation of metadata command"""
    try:
        config = _build_config(**kwargs)
        output_file = kwargs.get('output', './metadata.json')
        
        click.echo(f"\nExporting metadata from: {config.service_url}")
        
        connector = SAPODataConnector(config)
        
        try:
            info = await connector.initialize()
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, default=str)
            
            file_size = Path(output_file).stat().st_size / 1024
            
            click.echo(f"✓ Metadata exported successfully!")
            click.echo(f"  - File: {output_file}")
            click.echo(f"  - Size: {file_size:.2f} KB")
            click.echo(f"  - Entities: {info['total_entities']}")
            click.echo(f"  - Total Records: {info['total_records']:,}\n")
            
        finally:
            await connector.cleanup()
            
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        sys.exit(1)


def _build_config(**kwargs) -> ClientConfig:
    """Build ClientConfig from CLI arguments"""
    
    # Method 1: Full URL
    if kwargs.get('url'):
        return ClientConfig(
            service_url=kwargs['url'],
            username=kwargs.get('user'),
            password=kwargs.get('password'),
            output_directory=kwargs.get('output', './output'),
            timeout=kwargs.get('timeout', 60)
        )
    
    # Method 2: Server + Module/Service
    elif kwargs.get('server'):
        config_params = {
            'sap_server': kwargs['server'],
            'sap_port': kwargs.get('port', 443),
            'use_https': True,
            'username': kwargs.get('user'),
            'password': kwargs.get('password'),
            'output_directory': kwargs.get('output', './output'),
            'timeout': kwargs.get('timeout', 60)
        }
        
        if kwargs.get('module'):
            config_params['sap_module'] = kwargs['module']
        elif kwargs.get('service'):
            config_params['service_name'] = kwargs['service']
        
        return ClientConfig(**config_params)
    
    else:
        raise click.UsageError(
            "You must provide either:\n"
            "  --url <service-url>\n"
            "  OR\n"
            "  --server <hostname> --module <module-name>\n"
            "  OR\n"
            "  --server <hostname> --service <service-name>"
        )


if __name__ == '__main__':
    main()
