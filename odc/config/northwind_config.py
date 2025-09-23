"""Example configuration for Northwind OData service"""

# Northwind OData V4 Service Configuration
ODATA_CONNECTOR_ODATA_SERVICE_URL = "https://services.odata.org/V4/Northwind/Northwind.svc"

# No authentication required for Northwind (public service)
# ODATA_CONNECTOR_USERNAME = ""
# ODATA_CONNECTOR_PASSWORD = ""

# Processing settings
ODATA_CONNECTOR_SELECTED_MODULES = []  # Empty means all entities
ODATA_CONNECTOR_TOTAL_RECORDS_LIMIT = 1000  # Limit for testing
ODATA_CONNECTOR_BATCH_SIZE = 50  # Smaller batch size for testing
ODATA_CONNECTOR_MAX_WORKERS = 3  # Fewer workers for testing

# Rate limiting (be respectful to public service)
ODATA_CONNECTOR_REQUESTS_PER_SECOND = 2.0

# Local storage settings
ODATA_CONNECTOR_OUTPUT_DIRECTORY = "./northwind_output"
ODATA_CONNECTOR_RAW_DATA_DIRECTORY = "./northwind_output/raw"
ODATA_CONNECTOR_PROCESSED_DATA_DIRECTORY = "./northwind_output/processed"
