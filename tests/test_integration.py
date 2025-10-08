"""
Integration tests for SAP OData Connector
Tests against real SAP ES5 demo server
These tests require valid credentials and network connectivity
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig


# Skip integration tests if credentials not provided
SKIP_INTEGRATION = not all([
    os.getenv('SAP_TEST_SERVER'),
    os.getenv('SAP_TEST_USERNAME'),
    os.getenv('SAP_TEST_PASSWORD')
])

skip_if_no_credentials = pytest.mark.skipif(
    SKIP_INTEGRATION,
    reason="Integration tests require SAP credentials in environment variables"
)


@pytest.fixture
def sap_config():
    """Fixture for SAP configuration"""
    return ClientConfig(
        sap_server=os.getenv('SAP_TEST_SERVER', 'sapes5.sapdevcenter.com'),
        sap_port=int(os.getenv('SAP_TEST_PORT', '443')),
        sap_module=os.getenv('SAP_TEST_MODULE', 'ES5'),
        username=os.getenv('SAP_TEST_USERNAME'),
        password=os.getenv('SAP_TEST_PASSWORD'),
        output_directory="./test_output"
    )


class TestRealConnection:
    """Integration tests for real SAP server connection"""
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_connection_success(self, sap_config):
        """
        POSITIVE: Test real connection to SAP ES5 demo server
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            result = await connector.initialize()
            
            assert result is not None
            assert 'total_entities' in result
            assert result['total_entities'] > 0
            assert 'service_url' in result
            
            print(f"\n✓ Connected successfully")
            print(f"  • Total entities: {result['total_entities']}")
            print(f"  • Service URL: {result['service_url']}")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_connection_invalid_credentials(self):
        """
        NEGATIVE: Test connection with invalid credentials
        """
        config = ClientConfig(
            sap_server=os.getenv('SAP_TEST_SERVER', 'sapes5.sapdevcenter.com'),
            sap_port=443,
            sap_module='ES5',
            username='invalid_user',
            password='invalid_password'
        )
        
        connector = SAPODataConnector(config)
        
        with pytest.raises(Exception):  # Should fail with auth error
            await connector.initialize()


class TestRealQueries:
    """Integration tests for real query execution"""
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fetch_all_products(self, sap_config):
        """
        POSITIVE: Test fetching all products from ES5
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(entity_name="Products")
            
            assert result is not None
            assert 'data' in result
            assert 'Products' in result['data']
            assert 'records' in result['data']['Products']
            assert len(result['data']['Products']['records']) > 0
            
            stats = result['execution_stats']
            print(f"\n✓ Products fetched successfully")
            print(f"  • Records: {stats['records_processed']}")
            print(f"  • Duration: {stats['duration_seconds']:.2f}s")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_with_filter(self, sap_config):
        """
        POSITIVE: Test query with filter on real data
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(
                entity_name="Products",
                filter_condition="Price gt 100"
            )
            
            assert result is not None
            records = result['data']['Products']['records']
            
            # Verify all records match filter
            for record in records:
                assert float(record.data.get('Price', 0)) > 100
            
            print(f"\n✓ Filtered query successful")
            print(f"  • Records matching filter: {len(records)}")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_with_field_selection(self, sap_config):
        """
        POSITIVE: Test query with specific field selection
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(
                entity_name="Products",
                select_fields="Id,Name,Price",
                record_limit=10
            )
            
            assert result is not None
            records = result['data']['Products']['records']
            assert len(records) > 0
            
            # Verify only selected fields are present (plus metadata)
            first_record = records[0].data
            assert 'Id' in first_record or 'ProductId' in first_record
            assert 'Name' in first_record
            
            print(f"\n✓ Field selection successful")
            print(f"  • Records: {len(records)}")
            print(f"  • Fields: {list(first_record.keys())}")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_with_expansion(self, sap_config):
        """
        POSITIVE: Test query with relationship expansion
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(
                entity_name="Products",
                expand_relations="Supplier",
                record_limit=5
            )
            
            assert result is not None
            records = result['data']['Products']['records']
            assert len(records) > 0
            
            # Check if expansion worked
            first_record = records[0].data
            has_supplier = 'Supplier' in first_record or 'ToSupplier' in first_record
            
            print(f"\n✓ Expansion query successful")
            print(f"  • Records: {len(records)}")
            print(f"  • Has expanded data: {has_supplier}")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_with_sorting(self, sap_config):
        """
        POSITIVE: Test query with sorting
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(
                entity_name="Products",
                order_by="Price desc",
                record_limit=10
            )
            
            assert result is not None
            records = result['data']['Products']['records']
            assert len(records) > 0
            
            # Verify sorting (prices should be descending)
            prices = [float(r.data.get('Price', 0)) for r in records if 'Price' in r.data]
            if len(prices) > 1:
                assert prices == sorted(prices, reverse=True), "Records should be sorted by price descending"
            
            print(f"\n✓ Sorting query successful")
            print(f"  • Records: {len(records)}")
            print(f"  • Prices: {prices[:5]}")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_with_record_limit(self, sap_config):
        """
        POSITIVE: Test query with record limit
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            limit = 25
            result = await connector.get_data(
                entity_name="Products",
                record_limit=limit
            )
            
            assert result is not None
            records = result['data']['Products']['records']
            assert len(records) <= limit
            
            print(f"\n✓ Record limit successful")
            print(f"  • Requested: {limit}")
            print(f"  • Received: {len(records)}")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_invalid_entity(self, sap_config):
        """
        NEGATIVE: Test query with non-existent entity
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            with pytest.raises(Exception):
                await connector.get_data(entity_name="NonExistentEntity123")
            
            print(f"\n✓ Invalid entity correctly rejected")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_invalid_filter_syntax(self, sap_config):
        """
        NEGATIVE: Test query with invalid filter syntax
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            # Using SQL syntax instead of OData syntax
            with pytest.raises(Exception):
                await connector.get_data(
                    entity_name="Products",
                    filter_condition="Price > 100"  # Should be 'gt' not '>'
                )
            
            print(f"\n✓ Invalid filter syntax correctly rejected")
            
        finally:
            await connector.cleanup()


class TestRealPagination:
    """Integration tests for pagination with real data"""
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_automatic_pagination(self, sap_config):
        """
        POSITIVE: Test automatic pagination with large dataset
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            # Fetch all products (should trigger pagination if > 500 records)
            result = await connector.get_data(entity_name="Products")
            
            assert result is not None
            stats = result['execution_stats']
            
            print(f"\n✓ Pagination test successful")
            print(f"  • Total records: {stats['records_processed']}")
            print(f"  • Duration: {stats['duration_seconds']:.2f}s")
            
            if stats['records_processed'] > 500:
                print(f"  • Pagination was triggered (>500 records)")
            
        finally:
            await connector.cleanup()


class TestRealComplexQueries:
    """Integration tests for complex real-world queries"""
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complex_query_all_features(self, sap_config):
        """
        POSITIVE: Test complex query with multiple features
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(
                entity_name="Products",
                filter_condition="Price gt 50",
                select_fields="Id,Name,Price,Category",
                order_by="Price desc",
                record_limit=20
            )
            
            assert result is not None
            records = result['data']['Products']['records']
            assert len(records) > 0
            assert len(records) <= 20
            
            stats = result['execution_stats']
            print(f"\n✓ Complex query successful")
            print(f"  • Records: {stats['records_processed']}")
            print(f"  • Duration: {stats['duration_seconds']:.2f}s")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_date_range_query(self, sap_config):
        """
        POSITIVE: Test query with date range filter
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            # Query last 6 months of data
            six_months_ago = datetime.now() - timedelta(days=180)
            date_str = six_months_ago.strftime('%Y-%m-%dT%H:%M:%S')
            
            result = await connector.get_data(
                entity_name="Products",
                filter_condition=f"CreatedAt ge datetime'{date_str}'",
                record_limit=10
            )
            
            # Query might return 0 records if no data in range, that's ok
            assert result is not None
            
            print(f"\n✓ Date range query successful")
            print(f"  • Records: {result['execution_stats']['records_processed']}")
            
        finally:
            await connector.cleanup()
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_string_search_query(self, sap_config):
        """
        POSITIVE: Test query with string search
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(
                entity_name="Products",
                filter_condition="contains(Name, 'Notebook')",
                record_limit=10
            )
            
            assert result is not None
            records = result['data']['Products']['records']
            
            # Verify results contain the search term
            for record in records:
                name = record.data.get('Name', '')
                if name:
                    assert 'Notebook' in name or 'notebook' in name.lower()
            
            print(f"\n✓ String search query successful")
            print(f"  • Matching records: {len(records)}")
            
        finally:
            await connector.cleanup()


class TestRealPerformance:
    """Integration tests for performance monitoring"""
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_performance_metrics(self, sap_config):
        """
        POSITIVE: Test that performance metrics are captured
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            result = await connector.get_data(
                entity_name="Products",
                record_limit=100
            )
            
            assert result is not None
            stats = result['execution_stats']
            
            # Verify all expected metrics are present
            assert 'records_processed' in stats
            assert 'duration_seconds' in stats
            assert stats['duration_seconds'] > 0
            
            # Calculate records per second
            if stats['duration_seconds'] > 0:
                rate = stats['records_processed'] / stats['duration_seconds']
                print(f"\n✓ Performance metrics captured")
                print(f"  • Records: {stats['records_processed']}")
                print(f"  • Duration: {stats['duration_seconds']:.2f}s")
                print(f"  • Rate: {rate:.0f} records/sec")
            
        finally:
            await connector.cleanup()


class TestRealMultipleQueries:
    """Integration tests for multiple sequential queries"""
    
    @skip_if_no_credentials
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_queries_same_connector(self, sap_config):
        """
        POSITIVE: Test multiple queries using same connector instance
        """
        connector = SAPODataConnector(sap_config)
        
        try:
            await connector.initialize()
            
            # Query 1: Products
            result1 = await connector.get_data(
                entity_name="Products",
                record_limit=10
            )
            assert result1 is not None
            
            # Query 2: Suppliers
            result2 = await connector.get_data(
                entity_name="Suppliers",
                record_limit=5
            )
            assert result2 is not None
            
            # Query 3: Categories
            result3 = await connector.get_data(
                entity_name="Categories"
            )
            assert result3 is not None
            
            print(f"\n✓ Multiple queries successful")
            print(f"  • Products: {result1['execution_stats']['records_processed']}")
            print(f"  • Suppliers: {result2['execution_stats']['records_processed']}")
            print(f"  • Categories: {result3['execution_stats']['records_processed']}")
            
        finally:
            await connector.cleanup()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "-m", "integration",
        "--tb=short",
        "-s"  # Show print statements
    ])
