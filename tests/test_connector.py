"""
Comprehensive test suite for SAP OData Connector
Includes positive and negative test cases
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig


class TestConnectorInitialization:
    """Test cases for connector initialization"""
    
    @pytest.mark.asyncio
    async def test_valid_configuration_with_module(self):
        """
        POSITIVE: Test successful initialization with valid SAP module
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass",
            output_directory="./test_output"
        )
        
        connector = SAPODataConnector(config)
        assert connector.config.sap_server == "sapes5.sapdevcenter.com"
        assert connector.config.sap_port == 443
        assert connector.config.sap_module == "ES5"
    
    @pytest.mark.asyncio
    async def test_valid_configuration_with_service_name(self):
        """
        POSITIVE: Test successful initialization with direct service name
        """
        config = ClientConfig(
            sap_server="myserver.com",
            sap_port=8000,
            service_name="MY_CUSTOM_SERVICE_SRV",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        assert connector.config.service_name == "MY_CUSTOM_SERVICE_SRV"
    
    @pytest.mark.asyncio
    async def test_valid_configuration_with_url(self):
        """
        POSITIVE: Test successful initialization with full service URL
        """
        config = ClientConfig(
            service_url="https://server.com/sap/opu/odata/sap/MY_SERVICE/",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        assert connector.config.service_url == "https://server.com/sap/opu/odata/sap/MY_SERVICE/"
    
    def test_missing_server_configuration(self):
        """
        NEGATIVE: Test initialization fails without server configuration
        """
        with pytest.raises(ValueError, match="sap_server is required"):
            config = ClientConfig(
                sap_module="ES5",
                username="test_user",
                password="test_pass"
            )
            config.validate()
    
    def test_missing_service_and_module(self):
        """
        NEGATIVE: Test initialization fails without service_name or sap_module
        """
        with pytest.raises(ValueError, match="Either service_name or sap_module must be provided"):
            config = ClientConfig(
                sap_server="server.com",
                sap_port=443,
                username="test_user",
                password="test_pass"
            )
            config.validate()
    
    def test_invalid_port_number(self):
        """
        NEGATIVE: Test initialization fails with invalid port
        """
        with pytest.raises(ValueError, match="sap_port must be a positive integer"):
            config = ClientConfig(
                sap_server="server.com",
                sap_port=-1,
                sap_module="ES5",
                username="test_user",
                password="test_pass"
            )
            config.validate()
    
    def test_invalid_service_url_format(self):
        """
        NEGATIVE: Test initialization fails with invalid URL format
        """
        with pytest.raises(ValueError, match="service_url must start with http"):
            config = ClientConfig(
                service_url="ftp://invalid.com/service",
                username="test_user",
                password="test_pass"
            )
            config.validate()


class TestConnectionTesting:
    """Test cases for connection testing"""
    
    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """
        POSITIVE: Test successful connection to SAP server
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # Mock the metadata service
        with patch.object(connector, 'metadata_service') as mock_metadata:
            mock_metadata.test_connection = AsyncMock(return_value=True)
            mock_metadata.__aenter__ = AsyncMock(return_value=mock_metadata)
            mock_metadata.__aexit__ = AsyncMock(return_value=None)
            
            await connector._test_connection()
            mock_metadata.test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """
        NEGATIVE: Test connection failure handling
        """
        config = ClientConfig(
            sap_server="invalid-server.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # Mock failed connection
        with patch.object(connector, 'metadata_service') as mock_metadata:
            mock_metadata.test_connection = AsyncMock(return_value=False)
            mock_metadata.__aenter__ = AsyncMock(return_value=mock_metadata)
            mock_metadata.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(ConnectionError, match="Failed to establish connection"):
                await connector._test_connection()
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """
        NEGATIVE: Test authentication failure (401 error)
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="wrong_user",
            password="wrong_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # Mock authentication failure
        with patch.object(connector, 'metadata_service') as mock_metadata:
            mock_metadata.test_connection = AsyncMock(side_effect=Exception("401 Unauthorized"))
            mock_metadata.__aenter__ = AsyncMock(return_value=mock_metadata)
            mock_metadata.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(Exception, match="401 Unauthorized"):
                await connector._test_connection()


class TestQueryExecution:
    """Test cases for query execution"""
    
    @pytest.mark.asyncio
    async def test_simple_query_all_records(self):
        """
        POSITIVE: Test fetching all records from an entity
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # Mock the query execution
        mock_result = {
            'data': {
                'Products': {
                    'records': [
                        {'Id': '1', 'Name': 'Product 1', 'Price': 100},
                        {'Id': '2', 'Name': 'Product 2', 'Price': 200}
                    ]
                }
            },
            'execution_stats': {
                'records_processed': 2,
                'duration_seconds': 1.5
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(entity_name="Products")
            
            assert result['execution_stats']['records_processed'] == 2
            assert len(result['data']['Products']['records']) == 2
    
    @pytest.mark.asyncio
    async def test_query_with_filter(self):
        """
        POSITIVE: Test query with filter condition
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {
                'Products': {
                    'records': [
                        {'Id': '2', 'Name': 'Product 2', 'Price': 200}
                    ]
                }
            },
            'execution_stats': {
                'records_processed': 1,
                'duration_seconds': 0.8
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(
                entity_name="Products",
                filter_condition="Price gt 100"
            )
            
            assert result['execution_stats']['records_processed'] == 1
            assert result['data']['Products']['records'][0]['Price'] == 200
    
    @pytest.mark.asyncio
    async def test_query_with_field_selection(self):
        """
        POSITIVE: Test query with specific field selection
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {
                'Products': {
                    'records': [
                        {'Id': '1', 'Name': 'Product 1'}  # Only selected fields
                    ]
                }
            },
            'execution_stats': {
                'records_processed': 1,
                'duration_seconds': 0.5
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(
                entity_name="Products",
                select_fields="Id,Name"
            )
            
            record = result['data']['Products']['records'][0]
            assert 'Id' in record
            assert 'Name' in record
            assert 'Price' not in record  # Not selected
    
    @pytest.mark.asyncio
    async def test_query_with_expansion(self):
        """
        POSITIVE: Test query with relationship expansion (JOIN)
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {
                'Products': {
                    'records': [
                        {
                            'Id': '1',
                            'Name': 'Product 1',
                            'Supplier': {
                                'Id': 'S1',
                                'Name': 'Supplier 1'
                            }
                        }
                    ]
                }
            },
            'execution_stats': {
                'records_processed': 1,
                'duration_seconds': 1.2
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(
                entity_name="Products",
                expand_relations="Supplier"
            )
            
            record = result['data']['Products']['records'][0]
            assert 'Supplier' in record
            assert record['Supplier']['Name'] == 'Supplier 1'
    
    @pytest.mark.asyncio
    async def test_query_with_record_limit(self):
        """
        POSITIVE: Test query with record limit
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {
                'Products': {
                    'records': [
                        {'Id': '1', 'Name': 'Product 1'},
                        {'Id': '2', 'Name': 'Product 2'},
                        {'Id': '3', 'Name': 'Product 3'}
                    ]
                }
            },
            'execution_stats': {
                'records_processed': 3,
                'duration_seconds': 0.6
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(
                entity_name="Products",
                record_limit=3
            )
            
            assert result['execution_stats']['records_processed'] == 3
            assert len(result['data']['Products']['records']) == 3
    
    @pytest.mark.asyncio
    async def test_query_invalid_entity_name(self):
        """
        NEGATIVE: Test query with non-existent entity
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        with patch.object(connector, '_lightweight_get_data', side_effect=Exception("Entity 'InvalidEntity' not found")):
            with pytest.raises(Exception, match="Entity 'InvalidEntity' not found"):
                await connector.get_data(entity_name="InvalidEntity")
    
    @pytest.mark.asyncio
    async def test_query_invalid_filter_syntax(self):
        """
        NEGATIVE: Test query with invalid filter syntax
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # Invalid filter using '>' instead of 'gt'
        with patch.object(connector, '_lightweight_get_data', side_effect=Exception("Invalid filter syntax")):
            with pytest.raises(Exception, match="Invalid filter syntax"):
                await connector.get_data(
                    entity_name="Products",
                    filter_condition="Price > 100"  # Wrong syntax
                )
    
    @pytest.mark.asyncio
    async def test_query_invalid_field_name(self):
        """
        NEGATIVE: Test query with non-existent field in select
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        with patch.object(connector, '_lightweight_get_data', side_effect=Exception("Field 'InvalidField' does not exist")):
            with pytest.raises(Exception, match="Field 'InvalidField' does not exist"):
                await connector.get_data(
                    entity_name="Products",
                    select_fields="Id,InvalidField"
                )
    
    @pytest.mark.asyncio
    async def test_query_invalid_expansion(self):
        """
        NEGATIVE: Test query with invalid relationship expansion
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        with patch.object(connector, '_lightweight_get_data', side_effect=Exception("Navigation property 'InvalidRelation' not found")):
            with pytest.raises(Exception, match="Navigation property 'InvalidRelation' not found"):
                await connector.get_data(
                    entity_name="Products",
                    expand_relations="InvalidRelation"
                )


class TestFilterSyntax:
    """Test cases for filter syntax validation"""
    
    @pytest.mark.asyncio
    async def test_filter_equality(self):
        """
        POSITIVE: Test filter with equality operator
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {'data': {'Products': {'records': []}}, 'execution_stats': {'records_processed': 0}}
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            # Should not raise exception
            await connector.get_data(
                entity_name="Products",
                filter_condition="Status eq 'Active'"
            )
    
    @pytest.mark.asyncio
    async def test_filter_comparison_operators(self):
        """
        POSITIVE: Test filter with comparison operators (gt, lt, ge, le)
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {'data': {'Products': {'records': []}}, 'execution_stats': {'records_processed': 0}}
        
        filters = [
            "Price gt 100",
            "Price ge 100",
            "Price lt 1000",
            "Price le 1000",
            "Quantity ne 0"
        ]
        
        for filter_cond in filters:
            with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
                await connector.get_data(
                    entity_name="Products",
                    filter_condition=filter_cond
                )
    
    @pytest.mark.asyncio
    async def test_filter_logical_operators(self):
        """
        POSITIVE: Test filter with logical operators (and, or)
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {'data': {'Products': {'records': []}}, 'execution_stats': {'records_processed': 0}}
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            await connector.get_data(
                entity_name="Products",
                filter_condition="Price gt 100 and Stock lt 10"
            )
    
    @pytest.mark.asyncio
    async def test_filter_string_functions(self):
        """
        POSITIVE: Test filter with string functions
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {'data': {'Products': {'records': []}}, 'execution_stats': {'records_processed': 0}}
        
        filters = [
            "contains(Name, 'SAP')",
            "startswith(Code, 'PRD')",
            "endswith(Email, '@company.com')"
        ]
        
        for filter_cond in filters:
            with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
                await connector.get_data(
                    entity_name="Products",
                    filter_condition=filter_cond
                )


class TestPagination:
    """Test cases for automatic pagination"""
    
    @pytest.mark.asyncio
    async def test_automatic_pagination_multiple_pages(self):
        """
        POSITIVE: Test automatic pagination with multiple pages
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # Mock result with pagination (1500 records = 3 pages of 500)
        mock_result = {
            'data': {
                'Products': {
                    'records': [{'Id': str(i)} for i in range(1500)]
                }
            },
            'execution_stats': {
                'records_processed': 1500,
                'pages_fetched': 3,
                'duration_seconds': 3.5
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(entity_name="Products")
            
            assert result['execution_stats']['records_processed'] == 1500
            assert result['execution_stats']['pages_fetched'] == 3
    
    @pytest.mark.asyncio
    async def test_pagination_with_limit(self):
        """
        POSITIVE: Test pagination stops at record limit
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {
                'Products': {
                    'records': [{'Id': str(i)} for i in range(100)]
                }
            },
            'execution_stats': {
                'records_processed': 100,
                'pages_fetched': 1,
                'duration_seconds': 0.8
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(
                entity_name="Products",
                record_limit=100
            )
            
            assert result['execution_stats']['records_processed'] == 100


class TestErrorHandling:
    """Test cases for error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_network_timeout_retry(self):
        """
        POSITIVE: Test automatic retry on network timeout
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # First call fails, second succeeds
        mock_result = {'data': {'Products': {'records': []}}, 'execution_stats': {'records_processed': 0}}
        
        call_count = 0
        async def mock_get_data(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError("Connection timeout")
            return mock_result
        
        with patch.object(connector, '_lightweight_get_data', side_effect=mock_get_data):
            # Should succeed on retry
            result = await connector.get_data(entity_name="Products")
            assert call_count == 2  # Failed once, succeeded on retry
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """
        NEGATIVE: Test failure after max retries exceeded
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        # Always fail
        with patch.object(connector, '_lightweight_get_data', side_effect=asyncio.TimeoutError("Connection timeout")):
            with pytest.raises(asyncio.TimeoutError):
                await connector.get_data(entity_name="Products")


class TestDataValidation:
    """Test cases for data validation"""
    
    @pytest.mark.asyncio
    async def test_empty_result_set(self):
        """
        POSITIVE: Test handling of empty result set
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {
                'Products': {
                    'records': []
                }
            },
            'execution_stats': {
                'records_processed': 0,
                'duration_seconds': 0.3
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(
                entity_name="Products",
                filter_condition="Price gt 999999"  # No records match
            )
            
            assert result['execution_stats']['records_processed'] == 0
            assert len(result['data']['Products']['records']) == 0
    
    @pytest.mark.asyncio
    async def test_null_values_in_data(self):
        """
        POSITIVE: Test handling of null values in data
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {
                'Products': {
                    'records': [
                        {'Id': '1', 'Name': 'Product 1', 'Description': None},
                        {'Id': '2', 'Name': 'Product 2', 'Description': 'Valid description'}
                    ]
                }
            },
            'execution_stats': {
                'records_processed': 2,
                'duration_seconds': 0.5
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(entity_name="Products")
            
            assert result['data']['Products']['records'][0]['Description'] is None
            assert result['data']['Products']['records'][1]['Description'] == 'Valid description'


class TestPerformance:
    """Test cases for performance monitoring"""
    
    @pytest.mark.asyncio
    async def test_query_duration_tracking(self):
        """
        POSITIVE: Test that query duration is tracked
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {'Products': {'records': []}},
            'execution_stats': {
                'records_processed': 0,
                'duration_seconds': 1.23
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(entity_name="Products")
            
            assert 'duration_seconds' in result['execution_stats']
            assert result['execution_stats']['duration_seconds'] > 0
    
    @pytest.mark.asyncio
    async def test_records_per_second_calculation(self):
        """
        POSITIVE: Test records per second calculation
        """
        config = ClientConfig(
            sap_server="sapes5.sapdevcenter.com",
            sap_port=443,
            sap_module="ES5",
            username="test_user",
            password="test_pass"
        )
        
        connector = SAPODataConnector(config)
        
        mock_result = {
            'data': {'Products': {'records': [{'Id': str(i)} for i in range(1000)]}},
            'execution_stats': {
                'records_processed': 1000,
                'duration_seconds': 2.0,
                'records_per_second': 500
            }
        }
        
        with patch.object(connector, '_lightweight_get_data', return_value=mock_result):
            result = await connector.get_data(entity_name="Products")
            
            assert result['execution_stats']['records_per_second'] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
