# main.py - Entry Point Documentation

## Overview
The `main.py` file serves as the command-line entry point for the SAP OData Connector. It provides a CLI interface for running data extraction jobs with configurable parameters.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
import sys
import argparse
from pathlib import Path
import structlog
from typing import Optional

from .connector import create_connector, SAPODataConnector
from .config.models import ConnectorSettings
```

**Concepts Explained:**
- **asyncio**: Python's asynchronous I/O library for concurrent programming
- **argparse**: Command-line argument parsing library
- **structlog**: Structured logging library for better log formatting and filtering
- **typing.Optional**: Type hint indicating a value can be None
- **Relative imports (.)**: Import from the same package using dot notation

### Logging Configuration
```python
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**Structured Logging Concepts:**
- **Processors**: Chain of functions that transform log records
- **filter_by_level**: Only process logs at or above configured level
- **add_logger_name**: Include logger name in output
- **add_log_level**: Include log level (INFO, ERROR, etc.)
- **TimeStamper**: Add ISO format timestamps
- **JSONRenderer**: Output logs as JSON for machine parsing
- **BoundLogger**: Logger that maintains context across calls

### Command Line Interface
```python
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SAP OData Connector - Extract data from SAP OData services",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Configuration options
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file (JSON/YAML)"
    )
    
    parser.add_argument(
        "--service-url", "-u",
        type=str,
        required=True,
        help="OData service URL"
    )
    
    # Authentication
    parser.add_argument("--username", type=str, help="Username for authentication")
    parser.add_argument("--password", type=str, help="Password for authentication")
    
    # Processing options
    parser.add_argument(
        "--entities", "-e",
        nargs="+",
        help="Specific entities to extract (default: all)"
    )
    
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=1000,
        help="Number of records per batch (default: 1000)"
    )
    
    parser.add_argument(
        "--max-workers", "-w",
        type=int,
        default=5,
        help="Maximum concurrent workers (default: 5)"
    )
    
    parser.add_argument(
        "--rate-limit", "-r",
        type=float,
        default=5.0,
        help="Requests per second limit (default: 5.0)"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="./output",
        help="Output directory for extracted data"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "csv", "parquet"],
        default="json",
        help="Output format (default: json)"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser
```

**CLI Design Patterns:**
- **Short and long options**: `-c` and `--config` for flexibility
- **Required arguments**: `required=True` for essential parameters
- **Type validation**: `type=int` ensures correct data types
- **Default values**: Sensible defaults for optional parameters
- **Choices**: Restrict values to valid options
- **nargs="+"**: Accept multiple values for entity list
- **action="store_true"**: Boolean flags

### Configuration Loading
```python
def load_config(args: argparse.Namespace) -> ConnectorSettings:
    """Load configuration from file and command line arguments"""
    
    # Start with file-based configuration if provided
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        settings = ConnectorSettings(config_file=str(config_path))
    else:
        settings = ConnectorSettings()
    
    # Override with command line arguments
    overrides = {}
    
    if args.service_url:
        overrides["odata_service_url"] = args.service_url
    if args.username:
        overrides["username"] = args.username
    if args.password:
        overrides["password"] = args.password
    if args.entities:
        overrides["selected_modules"] = args.entities
    if args.batch_size:
        overrides["batch_size"] = args.batch_size
    if args.max_workers:
        overrides["max_workers"] = args.max_workers
    if args.rate_limit:
        overrides["requests_per_second"] = args.rate_limit
    if args.output_dir:
        overrides["output_directory"] = args.output_dir
    
    # Apply overrides
    for key, value in overrides.items():
        setattr(settings.settings, key, value)
    
    return settings
```

**Configuration Management Concepts:**
- **File-first approach**: Load base config from file, then override with CLI args
- **Path validation**: Check if config file exists before loading
- **Dynamic attribute setting**: Use `setattr()` to modify configuration objects
- **Namespace object**: `argparse.Namespace` contains parsed CLI arguments

### Progress Reporting
```python
class ProgressReporter:
    """Handles progress reporting and user feedback"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = None
        self.last_update = None
        
    def on_start(self, total_entities: int):
        """Called when extraction starts"""
        self.start_time = asyncio.get_event_loop().time()
        print(f"🚀 Starting extraction of {total_entities} entities...")
        
    def on_progress(self, progress: dict):
        """Called periodically during extraction"""
        current_time = asyncio.get_event_loop().time()
        
        # Throttle updates to avoid spam
        if self.last_update and (current_time - self.last_update) < 2.0:
            return
            
        self.last_update = current_time
        
        completed = progress.get("completed_entities", 0)
        total = progress.get("total_entities", 0)
        records = progress.get("records_processed", 0)
        queue_size = progress.get("queue_size", 0)
        
        # Calculate progress percentage
        pct = (completed / total * 100) if total > 0 else 0
        
        # Calculate rate
        elapsed = current_time - self.start_time if self.start_time else 0
        rate = records / elapsed if elapsed > 0 else 0
        
        print(f"📊 Progress: {completed}/{total} entities ({pct:.1f}%) | "
              f"{records:,} records | {rate:.1f} records/sec | Queue: {queue_size}")
        
        if self.verbose:
            # Show additional details in verbose mode
            success_rate = progress.get("success_rate", 0)
            errors = progress.get("errors", 0)
            print(f"   Success rate: {success_rate:.1%} | Errors: {errors}")
    
    def on_complete(self, stats):
        """Called when extraction completes"""
        duration = stats.duration_seconds
        entities = stats.entities_processed
        records = stats.records_processed
        
        print(f"✅ Extraction completed in {duration:.2f}s")
        print(f"   Entities: {entities}")
        print(f"   Records: {records:,}")
        print(f"   Average rate: {records/duration:.1f} records/sec")
        
        if stats.commands_failed > 0:
            print(f"⚠️  {stats.commands_failed} commands failed")
```

**Progress Reporting Patterns:**
- **Event-driven design**: Separate methods for different lifecycle events
- **Rate limiting**: Throttle updates to avoid overwhelming output
- **Performance metrics**: Calculate rates and percentages
- **Conditional verbosity**: Show extra details only when requested
- **User-friendly formatting**: Use emojis and clear formatting

### Main Execution Function
```python
async def main():
    """Main execution function"""
    try:
        # Parse command line arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Configure logging level
        log_level = args.log_level
        if args.verbose:
            log_level = "DEBUG"
            
        logging.getLogger().setLevel(getattr(logging, log_level))
        
        # Load configuration
        settings = load_config(args)
        config = settings.get_client_config()
        
        # Create progress reporter
        reporter = ProgressReporter(verbose=args.verbose)
        
        # Create and configure connector
        connector = SAPODataConnector(config)
        
        # Set up callbacks
        connector.on_progress_update = reporter.on_progress
        
        # Initialize connector
        print("🔧 Initializing connector...")
        await connector.initialize()
        
        # Start extraction
        reporter.on_start(len(connector.metadata_service.schemas))
        stats = await connector.run(selected_entities=args.entities)
        
        # Report completion
        reporter.on_complete(stats)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Extraction cancelled by user")
        return 1
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
        
    finally:
        # Cleanup
        if 'connector' in locals() and connector.proxy_pool:
            await connector.proxy_pool.stop()
```

**Async Main Pattern:**
- **Exception handling**: Catch and handle different error types
- **Graceful shutdown**: Handle Ctrl+C interruption
- **Resource cleanup**: Ensure proper cleanup in finally block
- **Exit codes**: Return appropriate codes for shell scripting
- **Conditional debugging**: Show stack traces only in verbose mode

### Entry Point
```python
if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

**Entry Point Concepts:**
- **`__name__ == "__main__"`**: Only run when script is executed directly
- **asyncio.run()**: Run async function in event loop
- **sys.exit()**: Exit with specific code for shell integration

## Key Programming Concepts Used

### 1. **Asynchronous Programming**
- Event loop management with `asyncio.run()`
- Async/await pattern for non-blocking operations
- Concurrent execution without threading

### 2. **Command Line Interface Design**
- Argument parsing with type validation
- Short and long option formats
- Default values and help text
- Configuration file override pattern

### 3. **Structured Logging**
- JSON-formatted log output
- Log level filtering
- Contextual information preservation
- Machine-readable log format

### 4. **Configuration Management**
- File-based configuration with CLI overrides
- Environment variable support through dynaconf
- Type validation and default values

### 5. **Error Handling Patterns**
- Specific exception types for different errors
- Graceful degradation and user feedback
- Resource cleanup in finally blocks

### 6. **Progress Reporting**
- Event-driven progress updates
- Rate calculation and throttling
- User-friendly output formatting

## Usage Examples

### Basic Usage
```bash
python -m odc.main --service-url "https://services.odata.org/V4/Northwind/Northwind.svc"
```

### With Authentication
```bash
python -m odc.main \
  --service-url "https://your-sap-system.com/service/" \
  --username "your_user" \
  --password "your_pass" \
  --batch-size 500 \
  --max-workers 3
```

### Specific Entities
```bash
python -m odc.main \
  --service-url "https://services.odata.org/V4/Northwind/Northwind.svc" \
  --entities Categories Products Customers \
  --output-dir "./northwind_data" \
  --verbose
```

### With Configuration File
```bash
python -m odc.main --config config.yaml --verbose
```

## Customization Points

### 1. **Custom Progress Reporter**
```python
class CustomProgressReporter(ProgressReporter):
    def on_progress(self, progress: dict):
        # Send to monitoring system
        self.send_to_monitoring(progress)
        super().on_progress(progress)
```

### 2. **Additional CLI Arguments**
```python
parser.add_argument(
    "--filter",
    type=str,
    help="OData filter expression"
)
```

### 3. **Custom Configuration Loading**
```python
def load_custom_config(args):
    # Load from database, API, etc.
    pass
```

This file demonstrates enterprise-grade CLI design patterns, async programming, and user experience considerations for command-line tools.
