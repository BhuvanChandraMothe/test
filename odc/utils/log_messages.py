"""
Centralized log messages for SAP OData Connector
Provides consistent, informative messages throughout the application
"""

import structlog

logger = structlog.get_logger(__name__)


class LogMessages:
    """
    Centralized log messages with consistent formatting
    """
    
    @staticmethod
    def separator(char="=", length=80):
        """Print a separator line"""
        return char * length
    
    @staticmethod
    def phase_header(phase_num, total_phases, description):
        """Log a phase header"""
        logger.info(LogMessages.separator())
        logger.info(f"Phase {phase_num}/{total_phases}: {description}")
        logger.info(LogMessages.separator())
    
    @staticmethod
    def success(message, **kwargs):
        """Log a success message with checkmark"""
        logger.info(f"✓ {message}", **kwargs)
    
    @staticmethod
    def failure(message, **kwargs):
        """Log a failure message"""
        logger.error(f"✗ FAILED: {message}", **kwargs)
    
    @staticmethod
    def config_loaded(server, port, module, use_https, service_url):
        """Log configuration loaded"""
        logger.info("Configuration loaded successfully")
        logger.info(f"  • SAP Server: {server}")
        logger.info(f"  • Port: {port}")
        logger.info(f"  • Module/Service: {module}")
        logger.info(f"  • Protocol: {'HTTPS' if use_https else 'HTTP'}")
        logger.info(f"  • Service URL: {service_url}")
    
    @staticmethod
    def connection_testing(url):
        """Log connection test start"""
        logger.info("Testing connection to SAP OData service...")
        logger.info(f"  • Target URL: {url}")
        logger.info("  • Verifying network connectivity...")
        logger.info("  • Validating credentials...")
    
    @staticmethod
    def connection_success(response_time, status_code):
        """Log successful connection"""
        LogMessages.success(
            "Connection established successfully",
            response_time_seconds=f"{response_time:.2f}",
            http_status=status_code
        )
    
    @staticmethod
    def connection_failure(error, status_code=None):
        """Log connection failure with troubleshooting steps"""
        LogMessages.failure("Unable to connect to SAP server")
        logger.error(f"  • Error: {error}")
        if status_code:
            logger.error(f"  • HTTP Status: {status_code}")
        logger.error("")
        logger.error("Troubleshooting steps:")
        logger.error("  1. Verify SAP server URL is correct")
        logger.error("  2. Check network connectivity (ping the server)")
        logger.error("  3. Verify firewall allows outbound connections")
        logger.error("  4. Check if VPN is required and connected")
        logger.error("  5. Verify SAP service is running")
    
    @staticmethod
    def auth_failure(status_code):
        """Log authentication failure with troubleshooting"""
        LogMessages.failure("Authentication failed - Invalid credentials")
        logger.error(f"  • HTTP Status: {status_code} (Unauthorized)")
        logger.error("")
        logger.error("Please check:")
        logger.error("  1. Username is correct")
        logger.error("  2. Password is correct")
        logger.error("  3. User account is active and not locked")
        logger.error("  4. User has permission to access this SAP system")
        logger.error("  5. SAP client number is correct (if applicable)")
    
    @staticmethod
    def metadata_fetching():
        """Log metadata fetch start"""
        logger.info("Downloading OData service metadata...")
        logger.info("  • Fetching $metadata endpoint")
        logger.info("  • This contains entity schemas and relationships")
    
    @staticmethod
    def metadata_success(entity_count, relationship_count, size_kb, duration):
        """Log successful metadata fetch"""
        LogMessages.success(
            "Metadata retrieved and parsed successfully",
            entities_found=entity_count,
            relationships_found=relationship_count,
            metadata_size_kb=f"{size_kb:.1f}",
            duration_seconds=f"{duration:.2f}"
        )
    
    @staticmethod
    def entity_analysis_start(entity_count):
        """Log entity analysis start"""
        logger.info(f"Analyzing {entity_count} available entities...")
        logger.info("  • Counting records in each entity")
        logger.info("  • This helps optimize worker allocation")
    
    @staticmethod
    def entity_count(entity_name, record_count):
        """Log individual entity count"""
        logger.info(f"  • {entity_name}: {record_count:,} records")
    
    @staticmethod
    def entity_analysis_complete(total_entities, total_records):
        """Log entity analysis completion"""
        LogMessages.success(
            "Entity analysis complete",
            total_entities=total_entities,
            total_records=f"{total_records:,}"
        )
    
    @staticmethod
    def worker_pool_config(workers, connections, selected_entities):
        """Log worker pool configuration"""
        logger.info("Worker pool configuration calculated:")
        logger.info(f"  • Workers: {workers}")
        logger.info(f"  • Connections per worker: {connections // workers if workers > 0 else 0}")
        logger.info(f"  • Total connection pool size: {connections}")
        logger.info(f"  • Entities to process: {selected_entities}")
    
    @staticmethod
    def query_start(entity_name, filter_cond, select_fields, expand, order_by, limit):
        """Log query execution start"""
        logger.info(LogMessages.separator())
        logger.info(f"Executing Query: {entity_name}")
        logger.info(LogMessages.separator())
        logger.info("Query Parameters:")
        logger.info(f"  • Entity: {entity_name}")
        logger.info(f"  • Filter: {filter_cond or 'None (fetch all records)'}")
        logger.info(f"  • Select Fields: {select_fields or 'All fields'}")
        logger.info(f"  • Expand Relations: {expand or 'None'}")
        logger.info(f"  • Order By: {order_by or 'Default ordering'}")
        logger.info(f"  • Record Limit: {limit or 'Unlimited (fetch all)'}")
        logger.info(LogMessages.separator("-", 80))
    
    @staticmethod
    def pagination_progress(page_num, records_fetched, duration, total_so_far):
        """Log pagination progress"""
        logger.info(
            f"Page {page_num} fetched",
            records_this_page=records_fetched,
            duration_seconds=f"{duration:.2f}",
            total_records_so_far=f"{total_so_far:,}"
        )
    
    @staticmethod
    def query_complete(total_records, total_pages, total_requests, duration, rate):
        """Log query completion with statistics"""
        logger.info(LogMessages.separator("-", 80))
        LogMessages.success("Query execution completed")
        logger.info("Execution Statistics:")
        logger.info(f"  • Total records retrieved: {total_records:,}")
        logger.info(f"  • Total pages fetched: {total_pages}")
        logger.info(f"  • Total HTTP requests: {total_requests}")
        logger.info(f"  • Total duration: {duration:.2f} seconds")
        logger.info(f"  • Average rate: {rate:.0f} records/second")
        logger.info(LogMessages.separator("-", 80))
    
    @staticmethod
    def file_saved(file_path, size_kb):
        """Log file save success"""
        LogMessages.success(
            "Results saved to file",
            file_path=file_path,
            file_size_kb=f"{size_kb:.1f}"
        )
    
    @staticmethod
    def initialization_complete(total_entities, selected_entities, workers, connections, duration):
        """Log initialization completion summary"""
        logger.info(LogMessages.separator())
        LogMessages.success("SAP OData Connector Initialization Complete")
        logger.info(LogMessages.separator())
        logger.info("Initialization Summary:")
        logger.info(f"  • Total entities available: {total_entities}")
        logger.info(f"  • Entities selected for processing: {selected_entities}")
        logger.info(f"  • Worker pool size: {workers} workers")
        logger.info(f"  • Connection pool size: {connections} connections")
        logger.info(f"  • Initialization time: {duration:.2f} seconds")
        logger.info(LogMessages.separator())
        logger.info("✓ Ready to execute queries!")
        logger.info(LogMessages.separator())
    
    @staticmethod
    def filter_syntax_error(filter_str, error_msg, suggestion):
        """Log filter syntax error with helpful suggestion"""
        LogMessages.failure("Invalid filter syntax detected")
        logger.error(f"  • Your filter: {filter_str}")
        logger.error(f"  • Error: {error_msg}")
        logger.error(f"  • Suggestion: {suggestion}")
        logger.error("")
        logger.error("Common filter syntax:")
        logger.error("  • Comparison: Price gt 100")
        logger.error("  • Equality: Status eq 'Active'")
        logger.error("  • String contains: contains(Name, 'SAP')")
        logger.error("  • Date filter: OrderDate ge datetime'2024-01-01T00:00:00'")
        logger.error("")
        logger.error("See CONFIGURATION_AND_FILTERING_GUIDE.md for complete syntax reference")
    
    @staticmethod
    def retry_attempt(attempt, max_attempts, error):
        """Log retry attempt"""
        logger.warning(
            f"Request failed, retrying...",
            attempt=f"{attempt}/{max_attempts}",
            error=str(error)
        )
    
    @staticmethod
    def retry_success(attempt):
        """Log successful retry"""
        LogMessages.success(f"Request succeeded on retry attempt {attempt}")
    
    @staticmethod
    def large_dataset_warning(estimated_records, estimated_time):
        """Warn about large dataset"""
        logger.warning(f"Large dataset detected: ~{estimated_records:,} records")
        logger.warning(f"  • Estimated time: ~{estimated_time:.0f} seconds")
        logger.warning("  • Consider adding filters to reduce data volume")
        logger.warning("  • Or use record_limit parameter for testing")
    
    @staticmethod
    def performance_warning(duration, threshold):
        """Warn about slow performance"""
        logger.warning(
            "Query performance slower than expected",
            actual_duration=f"{duration:.2f}s",
            expected_threshold=f"<{threshold}s"
        )
        logger.warning("Performance tips:")
        logger.warning("  • Add filters to reduce data volume")
        logger.warning("  • Use select_fields to fetch only needed columns")
        logger.warning("  • Check network connectivity")
        logger.warning("  • Verify SAP server performance")
