import asyncio
import os
import shutil
import sys
import json
from datetime import datetime

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from odc.connector import SAPODataConnector
from odc.config.models import ClientConfig
from odc.monitoring.metrics import get_metrics_collector
from prometheus_client import push_to_gateway


PUSH_GATEWAY_URL = 'http://localhost:9091'
PROMETHEUS_JOB_NAME = 'sap_odata_connector'


def extract_clean_data(records):
    """Extract only actual data, removing metadata"""
    clean_records = []
    
    if not records:
        return clean_records
    
    for record in records:
        if hasattr(record, 'data'):
            # TransformedRecord object - extract the inner data
            inner_data = record.data
            if isinstance(inner_data, dict):
                # Remove OData metadata from inner data
                clean_record = {}
                for key, value in inner_data.items():
                    if not key.startswith('@odata') and key not in [
                        'transformed_at', 'metadata', 'entity_name', 'record_id'
                    ]:
                        clean_record[key] = value
                clean_records.append(clean_record)
            else:
                clean_records.append(inner_data)
        elif isinstance(record, dict):
            # Dictionary - remove OData metadata
            clean_record = {}
            for key, value in record.items():
                if not key.startswith('@odata') and key not in [
                    'transformed_at', 'metadata', 'entity_name', 'record_id'
                ]:
                    clean_record[key] = value
            clean_records.append(clean_record)
        else:
            clean_records.append(record)
    
    return clean_records


def save_test_data(data, filename):
    """Save test data to JSON file"""
    os.makedirs("./northwind_test_output", exist_ok=True)
    filepath = f"./northwind_test_output/{filename}"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    return filepath


async def test_northwind():
    """Complete filtering tests with clean data output and file saving"""
    
    print("TARGET: SAP ODATA CONNECTOR - NORTHWIND FILTERING TESTS")
    print("=" * 60)
    print("Testing all filtering methods with clean data output")
    print("=" * 60)
    
    # Clean up previous test output
    output_dir = "./northwind_test_output"
    if os.path.exists(output_dir):
        print(f"Cleanup: Cleaning up previous test output: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create configuration for SAP OData service
    config = ClientConfig(
        service_url="https://services.odata.org/V4/Northwind/Northwind.svc",
        output_directory=output_dir
    )
    
    # Use context manager for proper cleanup
    async with SAPODataConnector(config) as connector:
        
        test_results = {
            "test_timestamp": datetime.now().isoformat(),
            "service_url": config.service_url,
            "tests": {}
        }
        
        # TEST 1: Basic Products (no filter)
        print("\nTEST: TEST 1: Basic Products (No Filter)")
        print("-" * 40)
        
        try:
            result1 = await connector.get_data(
                entity_name="Products",
                select_fields="ProductID,ProductName,UnitPrice,CategoryID",
                batch_size=10,
                max_workers=1
            )
            
            records_count = result1['execution_stats']['records_processed']
            duration = result1['execution_stats']['duration_seconds']
            
            print(f" Retrieved {records_count} products in {duration:.2f}s")
            
            if 'Products' in result1['data'] and result1['data']['Products']['records']:
                clean_products = extract_clean_data(result1['data']['Products']['records'])
                # Limit to first 5 records for testing
                clean_products = clean_products[:5]
                test_results['tests']['basic_products'] = {
                    'records_count': len(clean_products),
                    'data': clean_products
                }
                
                # Save clean data
                filepath = save_test_data(clean_products, "basic_products.json")
                print(f" Saved to: {filepath}")
                
                # Display sample results
                print("RESULTS: BASIC PRODUCTS:")
                for i, product in enumerate(clean_products[:3], 1):
                    name = product.get('ProductName', 'N/A')
                    price = product.get('UnitPrice', 'N/A')
                    category = product.get('CategoryID', 'N/A')
                    print(f"   {i}. {name} - ${price} (Category: {category})")
            else:
                print("FAILED: No products data found")
                test_results['tests']['basic_products'] = {'error': 'No data found'}
                
        except Exception as e:
            print(f"FAILED: Test 1 failed: {e}")
            test_results['tests']['basic_products'] = {'error': str(e)}
        
        # TEST 2: Price Filtering
        print("\nTEST: TEST 2: Expensive Products (Price > $20)")
        print("-" * 40)
        
        try:
            result2 = await connector.get_data(
                entity_name="Products",
                filter_condition="UnitPrice gt 20",
                select_fields="ProductID,ProductName,UnitPrice",
                batch_size=10,
                max_workers=1
            )
            
            records_count = result2['execution_stats']['records_processed']
            duration = result2['execution_stats']['duration_seconds']
            
            print(f" Retrieved {records_count} expensive products in {duration:.2f}s")
            
            if 'Products' in result2['data'] and result2['data']['Products']['records']:
                clean_products = extract_clean_data(result2['data']['Products']['records'])
                # Limit to first 5 records for testing
                clean_products = clean_products[:5]
                test_results['tests']['expensive_products'] = {
                    'records_count': len(clean_products),
                    'filter_condition': 'UnitPrice gt 20',
                    'data': clean_products
                }
                
                # Save clean data
                filepath = save_test_data(clean_products, "expensive_products.json")
                print(f" Saved to: {filepath}")
                
                # Display sample results
                print("ధర: EXPENSIVE PRODUCTS:")
                for i, product in enumerate(clean_products[:3], 1):
                    name = product.get('ProductName', 'N/A')
                    price = product.get('UnitPrice', 'N/A')
                    print(f"   {i}. {name} - ${price}")
            else:
                print("FAILED: No expensive products found")
                test_results['tests']['expensive_products'] = {'error': 'No data found'}
                
        except Exception as e:
            print(f"FAILED: Test 2 failed: {e}")
            test_results['tests']['expensive_products'] = {'error': str(e)}
        
        # TEST 3: Category Filtering
        print("\nTEST: TEST 3: Beverages (Category 1)")
        print("-" * 40)
        
        try:
            result3 = await connector.get_data(
                entity_name="Products",
                filter_condition="CategoryID eq 1",
                select_fields="ProductID,ProductName,UnitPrice,CategoryID",
                batch_size=10,
                max_workers=1
            )
            
            records_count = result3['execution_stats']['records_processed']
            duration = result3['execution_stats']['duration_seconds']
            
            print(f" Retrieved {records_count} beverages in {duration:.2f}s")
            
            if 'Products' in result3['data'] and result3['data']['Products']['records']:
                clean_products = extract_clean_data(result3['data']['Products']['records'])
                # Limit to first 5 records for testing
                clean_products = clean_products[:5]
                test_results['tests']['beverages'] = {
                    'records_count': len(clean_products),
                    'filter_condition': 'CategoryID eq 1',
                    'data': clean_products
                }
                
                # Save clean data
                filepath = save_test_data(clean_products, "beverages.json")
                print(f" Saved to: {filepath}")
                
                # Display sample results
                print("పానీయాలు: BEVERAGES:")
                for i, product in enumerate(clean_products[:3], 1):
                    name = product.get('ProductName', 'N/A')
                    price = product.get('UnitPrice', 'N/A')
                    print(f"   {i}. {name} - ${price}")
            else:
                print("FAILED: No beverages found")
                test_results['tests']['beverages'] = {'error': 'No data found'}
                
        except Exception as e:
            print(f"FAILED: Test 3 failed: {e}")
            test_results['tests']['beverages'] = {'error': str(e)}
        
        # TEST 4: Sorting
        print("\nTEST: TEST 4: Most Expensive Products (Sorted)")
        print("-" * 40)
        
        try:
            result4 = await connector.get_data(
                entity_name="Products",
                select_fields="ProductID,ProductName,UnitPrice",
                order_by="UnitPrice desc",
                batch_size=10,
                max_workers=1
            )
            
            records_count = result4['execution_stats']['records_processed']
            duration = result4['execution_stats']['duration_seconds']
            
            print(f" Retrieved {records_count} sorted products in {duration:.2f}s")
            
            if 'Products' in result4['data'] and result4['data']['Products']['records']:
                clean_products = extract_clean_data(result4['data']['Products']['records'])
                # Limit to first 5 records for testing
                clean_products = clean_products[:5]
                test_results['tests']['sorted_products'] = {
                    'records_count': len(clean_products),
                    'order_by': 'UnitPrice desc',
                    'data': clean_products
                }
                
                # Save clean data
                filepath = save_test_data(clean_products, "sorted_products.json")
                print(f" Saved to: {filepath}")
                
                # Display sample results
                print("మొత్తం: MOST EXPENSIVE:")
                for i, product in enumerate(clean_products[:3], 1):
                    name = product.get('ProductName', 'N/A')
                    price = product.get('UnitPrice', 'N/A')
                    print(f"   {i}. {name} - ${price}")
            else:
                print("FAILED: No sorted products found")
                test_results['tests']['sorted_products'] = {'error': 'No data found'}
                
        except Exception as e:
            print(f"FAILED: Test 4 failed: {e}")
            test_results['tests']['sorted_products'] = {'error': str(e)}
        
        # TEST 5: Customer Filtering
        print("\nTEST: TEST 5: German Customers")
        print("-" * 40)
        
        try:
            result5 = await connector.get_data(
                entity_name="Customers",
                filter_condition="Country eq 'Germany'",
                select_fields="CustomerID,CompanyName,Country,City",
                batch_size=10,
                max_workers=1
            )
            
            records_count = result5['execution_stats']['records_processed']
            duration = result5['execution_stats']['duration_seconds']
            
            print(f" Retrieved {records_count} German customers in {duration:.2f}s")
            
            if 'Customers' in result5['data'] and result5['data']['Customers']['records']:
                clean_customers = extract_clean_data(result5['data']['Customers']['records'])
                # Limit to first 5 records for testing
                clean_customers = clean_customers[:5]
                test_results['tests']['german_customers'] = {
                    'records_count': len(clean_customers),
                    'filter_condition': "Country eq 'Germany'",
                    'data': clean_customers
                }
                
                # Save clean data
                filepath = save_test_data(clean_customers, "german_customers.json")
                print(f" Saved to: {filepath}")
                
                # Display sample results
                print("జర్మనీ: GERMAN CUSTOMERS:")
                for i, customer in enumerate(clean_customers[:3], 1):
                    company = customer.get('CompanyName', 'N/A')
                    city = customer.get('City', 'N/A')
                    print(f"   {i}. {company} - {city}")
            else:
                print("FAILED: No German customers found")
                test_results['tests']['german_customers'] = {'error': 'No data found'}
                
        except Exception as e:
            print(f"FAILED: Test 5 failed: {e}")
            test_results['tests']['german_customers'] = {'error': str(e)}
        
        # Save complete test results
        complete_filepath = save_test_data(test_results, "complete_test_results.json")
        
        # Push metrics to Grafana
        try:
            metrics_collector = get_metrics_collector()
            push_to_gateway(
                PUSH_GATEWAY_URL,
                job=PROMETHEUS_JOB_NAME,
                registry=metrics_collector.registry
            )
            print("\nRESULTS: Metrics pushed to Grafana successfully!")
        except Exception as e:
            print(f"\nWARNING: Failed to push metrics: {e}")
        
        # Summary
        successful_tests = [name for name, test in test_results['tests'].items() if 'error' not in test]
        failed_tests = [name for name, test in test_results['tests'].items() if 'error' in test]
        
        print("\n" + "=" * 60)
        print("GREAT: NORTHWIND FILTERING TESTS COMPLETED!")
        print("=" * 60)
        print(f" Successful tests: {len(successful_tests)}")
        print(f"FAILED: Failed tests: {len(failed_tests)}")
        print(f" Results saved in: ./northwind_test_output/")
        print(f"పేజీ: Complete results: {complete_filepath}")
        
        if successful_tests:
            print("\nRESULTS: SUCCESSFUL TESTS:")
            for test_name in successful_tests:
                test_data = test_results['tests'][test_name]
                print(f"   • {test_name}: {test_data.get('records_count', 0)} records")
        
        if failed_tests:
            print("\nFAILED: FAILED TESTS:")
            for test_name in failed_tests:
                print(f"   • {test_name}")
        
        print("\nSETUP: FILTERING METHODS TESTED:")
        print("   • Basic data retrieval")
        print("   • Price filtering (UnitPrice gt 20)")
        print("   • Category filtering (CategoryID eq 1)")
        print("   • Sorting (order by UnitPrice desc)")
        print("   • Country filtering (Country eq 'Germany')")
        print("   • Field selection ($select)")
        
        return len(successful_tests) > 0


if __name__ == "__main__":
    print(" Running Simple SAP OData Filtering Tests...")
    success = asyncio.run(test_northwind())
    
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
    
    # Force exit to ensure no hanging
    import os
    os._exit(0 if success else 1)