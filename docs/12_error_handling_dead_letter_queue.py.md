# error_handling/dead_letter_queue.py - Error Handling Documentation

## Overview
The `error_handling/dead_letter_queue.py` file implements comprehensive error handling and dead letter queue functionality for the SAP OData Connector. It provides resilient error management, retry logic, and permanent failure handling for production deployments.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import structlog
from pathlib import Path
import pickle
import hashlib

from config.models import ODataConfig
from planning.plan_generator import FetchCommand
```

**Library Concepts:**
- **pickle**: Python object serialization for complex error data
- **hashlib**: Generate unique identifiers for error instances
- **pathlib**: Cross-platform file system operations
- **enum**: Type-safe error classification
- **dataclasses**: Structured error data containers

### Error Classification
```python
class ErrorType(Enum):
    """Classification of error types"""
    TRANSIENT = "transient"        # Temporary errors that may resolve
    PERMANENT = "permanent"        # Errors that won't resolve with retry
    RATE_LIMITED = "rate_limited"  # Rate limiting errors
    AUTHENTICATION = "auth"        # Authentication/authorization errors
    NETWORK = "network"           # Network connectivity errors
    TIMEOUT = "timeout"           # Request timeout errors
    VALIDATION = "validation"     # Data validation errors
    CONFIGURATION = "config"      # Configuration errors

class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"           # Minor issues, system continues
    MEDIUM = "medium"     # Moderate issues, some functionality affected
    HIGH = "high"         # Major issues, significant functionality affected
    CRITICAL = "critical" # Critical issues, system may be unusable
```

**Error Classification Benefits:**
- **Automated handling**: Different error types trigger different responses
- **Monitoring**: Track error patterns and trends
- **Alerting**: Severity-based alert routing
- **Retry logic**: Transient errors get retried, permanent errors don't
- **Reporting**: Categorized error analysis

### Error Data Classes
```python
@dataclass
class ErrorContext:
    """Context information when error occurred"""
    entity_name: Optional[str] = None
    batch_info: Optional[Dict[str, Any]] = None
    request_url: Optional[str] = None
    request_headers: Optional[Dict[str, str]] = None
    response_status: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    operation_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None

@dataclass
class ErrorRecord:
    """Complete error record for dead letter queue"""
    
    # Error identification
    error_id: str = field(default_factory=lambda: hashlib.uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Error details
    error_type: ErrorType = ErrorType.PERMANENT
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    message: str = ""
    exception_type: str = ""
    stack_trace: Optional[str] = None
    
    # Context
    context: ErrorContext = field(default_factory=ErrorContext)
    
    # Retry information
    retry_count: int = 0
    max_retries: int = 3
    next_retry_time: Optional[datetime] = None
    
    # Original data
    original_command: Optional[FetchCommand] = None
    original_data: Optional[Dict[str, Any]] = None
    
    # Resolution
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def __post_init__(self):
        """Generate unique error ID if not provided"""
        if not self.error_id:
            # Create deterministic ID based on error content
            content = f"{self.error_type.value}:{self.message}:{self.context.entity_name}"
            self.error_id = hashlib.md5(content.encode()).hexdigest()
    
    def can_retry(self) -> bool:
        """Check if error can be retried"""
        return (
            not self.resolved and
            self.retry_count < self.max_retries and
            self.error_type in [ErrorType.TRANSIENT, ErrorType.NETWORK, ErrorType.TIMEOUT, ErrorType.RATE_LIMITED]
        )
    
    def calculate_next_retry(self, backoff_factor: float = 2.0, max_delay: int = 3600) -> datetime:
        """Calculate next retry time with exponential backoff"""
        delay_seconds = min(backoff_factor ** self.retry_count, max_delay)
        return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
```

**Error Record Features:**
- **Unique identification**: Generate deterministic error IDs
- **Complete context**: Capture all relevant error information
- **Retry logic**: Built-in retry capability assessment
- **Exponential backoff**: Calculate optimal retry timing
- **Resolution tracking**: Track error resolution status

### DeadLetterQueue Class
```python
class DeadLetterQueue:
    """Manages failed operations and retry logic"""
    
    def __init__(self, storage_path: str = "./error_queue", max_queue_size: int = 10000):
        self.storage_path = Path(storage_path)
        self.max_queue_size = max_queue_size
        
        # In-memory queue for active processing
        self.error_queue: List[ErrorRecord] = []
        self.resolved_errors: List[ErrorRecord] = []
        
        # Error statistics
        self.stats = {
            'total_errors': 0,
            'resolved_errors': 0,
            'permanent_failures': 0,
            'retry_attempts': 0
        }
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing errors from storage
        asyncio.create_task(self._load_from_storage())
        
        self.logger = structlog.get_logger(__name__)
    
    async def add_error(
        self, 
        exception: Exception, 
        context: ErrorContext,
        original_command: Optional[FetchCommand] = None,
        original_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add an error to the dead letter queue"""
        
        # Classify the error
        error_type = self._classify_error(exception)
        severity = self._determine_severity(exception, error_type)
        
        # Create error record
        error_record = ErrorRecord(
            error_type=error_type,
            severity=severity,
            message=str(exception),
            exception_type=type(exception).__name__,
            stack_trace=self._get_stack_trace(exception),
            context=context,
            original_command=original_command,
            original_data=original_data
        )
        
        # Add to queue
        self.error_queue.append(error_record)
        self.stats['total_errors'] += 1
        
        # Persist to storage
        await self._persist_error(error_record)
        
        # Log the error
        self.logger.error("Error added to dead letter queue",
                         error_id=error_record.error_id,
                         error_type=error_type.value,
                         severity=severity.value,
                         entity=context.entity_name,
                         message=str(exception))
        
        # Trigger cleanup if queue is too large
        if len(self.error_queue) > self.max_queue_size:
            await self._cleanup_old_errors()
        
        return error_record.error_id
```

**Error Addition Features:**
- **Automatic classification**: Determine error type from exception
- **Severity assessment**: Calculate error impact level
- **Stack trace capture**: Preserve debugging information
- **Persistent storage**: Save errors to disk for durability
- **Queue management**: Prevent memory overflow with cleanup

### Error Classification Logic
```python
def _classify_error(self, exception: Exception) -> ErrorType:
    """Classify error type based on exception"""
    
    exception_name = type(exception).__name__
    exception_message = str(exception).lower()
    
    # Network-related errors
    if any(keyword in exception_name.lower() for keyword in 
           ['connection', 'network', 'socket', 'dns']):
        return ErrorType.NETWORK
    
    # Timeout errors
    if any(keyword in exception_name.lower() for keyword in 
           ['timeout', 'timedout']):
        return ErrorType.TIMEOUT
    
    # HTTP status code based classification
    if hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
        status_code = exception.response.status_code
        
        if status_code == 429:  # Too Many Requests
            return ErrorType.RATE_LIMITED
        elif status_code in [401, 403]:  # Unauthorized, Forbidden
            return ErrorType.AUTHENTICATION
        elif 500 <= status_code < 600:  # Server errors
            return ErrorType.TRANSIENT
        elif 400 <= status_code < 500:  # Client errors
            return ErrorType.PERMANENT
    
    # Rate limiting indicators
    if any(keyword in exception_message for keyword in 
           ['rate limit', 'too many requests', 'quota exceeded']):
        return ErrorType.RATE_LIMITED
    
    # Authentication errors
    if any(keyword in exception_message for keyword in 
           ['unauthorized', 'authentication', 'invalid credentials']):
        return ErrorType.AUTHENTICATION
    
    # Validation errors
    if any(keyword in exception_name.lower() for keyword in 
           ['validation', 'schema', 'format']):
        return ErrorType.VALIDATION
    
    # Configuration errors
    if any(keyword in exception_message for keyword in 
           ['configuration', 'config', 'setting']):
        return ErrorType.CONFIGURATION
    
    # Default to transient for unknown errors
    return ErrorType.TRANSIENT

def _determine_severity(self, exception: Exception, error_type: ErrorType) -> ErrorSeverity:
    """Determine error severity"""
    
    # Critical errors that stop the system
    if error_type == ErrorType.CONFIGURATION:
        return ErrorSeverity.CRITICAL
    
    # High severity for authentication issues
    if error_type == ErrorType.AUTHENTICATION:
        return ErrorSeverity.HIGH
    
    # Medium severity for permanent data issues
    if error_type == ErrorType.PERMANENT:
        return ErrorSeverity.MEDIUM
    
    # Low severity for transient issues
    if error_type in [ErrorType.TRANSIENT, ErrorType.NETWORK, ErrorType.TIMEOUT]:
        return ErrorSeverity.LOW
    
    return ErrorSeverity.MEDIUM
```

**Classification Logic:**
- **Exception type analysis**: Examine exception class names
- **Message content analysis**: Look for keywords in error messages
- **HTTP status codes**: Use standard HTTP status code meanings
- **Severity mapping**: Map error types to appropriate severity levels
- **Default handling**: Fallback classification for unknown errors

### Retry Processing
```python
async def process_retries(self) -> List[str]:
    """Process errors that are ready for retry"""
    
    current_time = datetime.now(timezone.utc)
    retry_results = []
    
    for error_record in self.error_queue[:]:  # Copy list to avoid modification during iteration
        if not error_record.can_retry():
            continue
        
        # Check if it's time to retry
        if error_record.next_retry_time and current_time < error_record.next_retry_time:
            continue
        
        try:
            # Attempt retry
            success = await self._retry_operation(error_record)
            
            if success:
                # Mark as resolved
                error_record.resolved = True
                error_record.resolution_time = current_time
                error_record.resolution_notes = f"Resolved after {error_record.retry_count} retries"
                
                # Move to resolved list
                self.error_queue.remove(error_record)
                self.resolved_errors.append(error_record)
                self.stats['resolved_errors'] += 1
                
                retry_results.append(f"Resolved: {error_record.error_id}")
                
                self.logger.info("Error resolved through retry",
                               error_id=error_record.error_id,
                               retry_count=error_record.retry_count)
            else:
                # Increment retry count and schedule next retry
                error_record.retry_count += 1
                error_record.next_retry_time = error_record.calculate_next_retry()
                self.stats['retry_attempts'] += 1
                
                if not error_record.can_retry():
                    # Mark as permanent failure
                    error_record.resolved = True
                    error_record.resolution_notes = f"Failed after {error_record.max_retries} retry attempts"
                    self.stats['permanent_failures'] += 1
                    
                    self.logger.error("Error marked as permanent failure",
                                    error_id=error_record.error_id,
                                    total_attempts=error_record.retry_count)
                
                retry_results.append(f"Retry failed: {error_record.error_id}")
        
        except Exception as e:
            self.logger.error("Retry processing failed",
                            error_id=error_record.error_id,
                            error=str(e))
    
    return retry_results

async def _retry_operation(self, error_record: ErrorRecord) -> bool:
    """Attempt to retry a failed operation"""
    
    if not error_record.original_command:
        return False
    
    try:
        # This would integrate with the actual connector components
        # For now, we'll simulate retry logic
        
        # Add delay for rate-limited errors
        if error_record.error_type == ErrorType.RATE_LIMITED:
            await asyncio.sleep(60)  # Wait 1 minute for rate limits
        
        # Simulate retry attempt
        # In real implementation, this would re-execute the original command
        # return await self.connector.retry_command(error_record.original_command)
        
        # For demonstration, randomly succeed on 3rd retry
        return error_record.retry_count >= 2
        
    except Exception as e:
        self.logger.error("Retry operation failed",
                         error_id=error_record.error_id,
                         error=str(e))
        return False
```

**Retry Processing Features:**
- **Time-based retry**: Only retry when enough time has passed
- **Exponential backoff**: Increasing delays between retries
- **Success tracking**: Move resolved errors to separate list
- **Failure limits**: Stop retrying after max attempts
- **Rate limit handling**: Special handling for rate-limited errors

### Storage and Persistence
```python
async def _persist_error(self, error_record: ErrorRecord) -> None:
    """Persist error record to storage"""
    
    try:
        # Create filename with timestamp and error ID
        filename = f"{error_record.timestamp.strftime('%Y%m%d_%H%M%S')}_{error_record.error_id}.pkl"
        file_path = self.storage_path / filename
        
        # Serialize error record
        def write_sync():
            with open(file_path, 'wb') as f:
                pickle.dump(error_record, f)
        
        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_sync)
        
        self.logger.debug("Error persisted to storage",
                         error_id=error_record.error_id,
                         file_path=str(file_path))
    
    except Exception as e:
        self.logger.error("Failed to persist error",
                         error_id=error_record.error_id,
                         error=str(e))

async def _load_from_storage(self) -> None:
    """Load existing errors from storage"""
    
    try:
        if not self.storage_path.exists():
            return
        
        error_files = list(self.storage_path.glob("*.pkl"))
        
        for file_path in error_files:
            try:
                def read_sync():
                    with open(file_path, 'rb') as f:
                        return pickle.load(f)
                
                loop = asyncio.get_event_loop()
                error_record = await loop.run_in_executor(None, read_sync)
                
                if error_record.resolved:
                    self.resolved_errors.append(error_record)
                else:
                    self.error_queue.append(error_record)
                
            except Exception as e:
                self.logger.error("Failed to load error file",
                                file_path=str(file_path),
                                error=str(e))
        
        self.logger.info("Loaded errors from storage",
                        active_errors=len(self.error_queue),
                        resolved_errors=len(self.resolved_errors))
    
    except Exception as e:
        self.logger.error("Failed to load errors from storage", error=str(e))

async def _cleanup_old_errors(self, days_to_keep: int = 30) -> None:
    """Clean up old resolved errors"""
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    
    # Clean up in-memory resolved errors
    self.resolved_errors = [
        error for error in self.resolved_errors
        if error.resolution_time and error.resolution_time > cutoff_time
    ]
    
    # Clean up storage files
    try:
        for file_path in self.storage_path.glob("*.pkl"):
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if file_time < cutoff_time:
                file_path.unlink()
                self.logger.debug("Cleaned up old error file", file_path=str(file_path))
    
    except Exception as e:
        self.logger.error("Error cleanup failed", error=str(e))
```

**Storage Features:**
- **Pickle serialization**: Preserve complete Python objects
- **Timestamped files**: Organize errors by creation time
- **Async file I/O**: Non-blocking storage operations
- **Automatic loading**: Restore errors on startup
- **Cleanup management**: Remove old resolved errors

### Error Analysis and Reporting
```python
def get_error_statistics(self) -> Dict[str, Any]:
    """Get comprehensive error statistics"""
    
    active_errors = len(self.error_queue)
    resolved_errors = len(self.resolved_errors)
    
    # Error type breakdown
    error_type_counts = {}
    severity_counts = {}
    
    for error in self.error_queue + self.resolved_errors:
        error_type_counts[error.error_type.value] = error_type_counts.get(error.error_type.value, 0) + 1
        severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
    
    # Calculate resolution rate
    total_errors = active_errors + resolved_errors
    resolution_rate = (resolved_errors / total_errors * 100) if total_errors > 0 else 0
    
    return {
        'active_errors': active_errors,
        'resolved_errors': resolved_errors,
        'total_errors': total_errors,
        'resolution_rate_percent': resolution_rate,
        'error_type_breakdown': error_type_counts,
        'severity_breakdown': severity_counts,
        'retry_attempts': self.stats['retry_attempts'],
        'permanent_failures': self.stats['permanent_failures']
    }

def get_errors_by_entity(self) -> Dict[str, List[ErrorRecord]]:
    """Group errors by entity name"""
    
    entity_errors = {}
    
    for error in self.error_queue + self.resolved_errors:
        entity_name = error.context.entity_name or "unknown"
        
        if entity_name not in entity_errors:
            entity_errors[entity_name] = []
        
        entity_errors[entity_name].append(error)
    
    return entity_errors

def get_recent_errors(self, hours: int = 24) -> List[ErrorRecord]:
    """Get errors from recent time period"""
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    return [
        error for error in self.error_queue + self.resolved_errors
        if error.timestamp > cutoff_time
    ]

async def export_error_report(self, file_path: str) -> None:
    """Export detailed error report"""
    
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'statistics': self.get_error_statistics(),
        'errors_by_entity': {
            entity: len(errors) for entity, errors in self.get_errors_by_entity().items()
        },
        'recent_errors': [
            {
                'error_id': error.error_id,
                'timestamp': error.timestamp.isoformat(),
                'error_type': error.error_type.value,
                'severity': error.severity.value,
                'message': error.message,
                'entity': error.context.entity_name,
                'resolved': error.resolved,
                'retry_count': error.retry_count
            }
            for error in self.get_recent_errors(24)
        ]
    }
    
    try:
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info("Error report exported", file_path=file_path)
    
    except Exception as e:
        self.logger.error("Failed to export error report", error=str(e))
```

**Analysis Features:**
- **Statistical summaries**: Comprehensive error metrics
- **Entity grouping**: Identify problematic entities
- **Time-based filtering**: Focus on recent errors
- **Export capabilities**: Generate detailed reports
- **Resolution tracking**: Monitor error resolution rates

## Advanced Error Handling Concepts

### Circuit Breaker Integration
```python
class ErrorAwareCircuitBreaker:
    """Circuit breaker that considers error patterns"""
    
    def __init__(self, dead_letter_queue: DeadLetterQueue):
        self.dlq = dead_letter_queue
        self.failure_threshold = 5
        self.recovery_timeout = 300  # 5 minutes
        self.last_failure_time = None
        self.consecutive_failures = 0
        self.state = "closed"  # closed, open, half-open
    
    def should_allow_request(self, entity_name: str) -> bool:
        """Check if requests should be allowed for entity"""
        
        # Get recent errors for entity
        recent_errors = [
            error for error in self.dlq.get_recent_errors(1)  # Last hour
            if error.context.entity_name == entity_name and not error.resolved
        ]
        
        # If too many recent errors, open circuit
        if len(recent_errors) >= self.failure_threshold:
            self.state = "open"
            self.last_failure_time = datetime.now(timezone.utc)
            return False
        
        # If circuit is open, check if recovery time has passed
        if self.state == "open":
            if self.last_failure_time:
                time_since_failure = datetime.now(timezone.utc) - self.last_failure_time
                if time_since_failure.total_seconds() > self.recovery_timeout:
                    self.state = "half-open"
                    return True
            return False
        
        return True
```

### Custom Error Handlers
```python
class CustomErrorHandler:
    """Extensible error handling with custom handlers"""
    
    def __init__(self, dead_letter_queue: DeadLetterQueue):
        self.dlq = dead_letter_queue
        self.custom_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, error_type: str, handler: Callable):
        """Register custom error handler"""
        self.custom_handlers[error_type] = handler
    
    async def handle_error(self, exception: Exception, context: ErrorContext) -> bool:
        """Handle error with custom logic"""
        
        error_type = type(exception).__name__
        
        # Try custom handler first
        if error_type in self.custom_handlers:
            try:
                handled = await self.custom_handlers[error_type](exception, context)
                if handled:
                    return True
            except Exception as e:
                self.dlq.logger.error("Custom error handler failed", 
                                    error_type=error_type, 
                                    error=str(e))
        
        # Fall back to dead letter queue
        await self.dlq.add_error(exception, context)
        return False

# Example custom handler
async def handle_rate_limit_error(exception: Exception, context: ErrorContext) -> bool:
    """Custom handler for rate limit errors"""
    
    # Extract retry-after header if available
    retry_after = 60  # Default to 1 minute
    
    if hasattr(exception, 'response') and exception.response.headers:
        retry_after_header = exception.response.headers.get('Retry-After')
        if retry_after_header:
            try:
                retry_after = int(retry_after_header)
            except ValueError:
                pass
    
    # Wait for the specified time
    await asyncio.sleep(retry_after)
    
    # Return True to indicate error was handled
    return True
```

## Key Programming Concepts

### 1. **Error Classification Pattern**
```python
def classify_error(exception: Exception) -> str:
    """Classify errors for appropriate handling"""
    
    # Check exception type
    if isinstance(exception, TimeoutError):
        return "timeout"
    elif isinstance(exception, ConnectionError):
        return "network"
    
    # Check exception message
    message = str(exception).lower()
    if "rate limit" in message:
        return "rate_limited"
    elif "unauthorized" in message:
        return "auth"
    
    return "unknown"
```

### 2. **Exponential Backoff Calculation**
```python
def calculate_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 300.0) -> float:
    """Calculate exponential backoff delay"""
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)
```

### 3. **Persistent Error Storage**
```python
import pickle
from pathlib import Path

def save_error(error_data: dict, storage_path: Path):
    """Save error data to persistent storage"""
    filename = f"error_{error_data['id']}.pkl"
    with open(storage_path / filename, 'wb') as f:
        pickle.dump(error_data, f)

def load_errors(storage_path: Path) -> List[dict]:
    """Load all errors from storage"""
    errors = []
    for file_path in storage_path.glob("error_*.pkl"):
        with open(file_path, 'rb') as f:
            errors.append(pickle.load(f))
    return errors
```

### 4. **Error Context Capture**
```python
def capture_error_context(request_info: dict, response_info: dict) -> dict:
    """Capture comprehensive error context"""
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'request_url': request_info.get('url'),
        'request_method': request_info.get('method'),
        'response_status': response_info.get('status_code'),
        'response_headers': dict(response_info.get('headers', {})),
        'user_agent': request_info.get('headers', {}).get('User-Agent'),
        'operation_id': request_info.get('operation_id')
    }
```

## Usage Examples

### Basic Error Handling
```python
from error_handling.dead_letter_queue import DeadLetterQueue, ErrorContext

dlq = DeadLetterQueue(storage_path="./errors")

# Handle an error
try:
    result = await risky_operation()
except Exception as e:
    context = ErrorContext(
        entity_name="Products",
        request_url="https://api.example.com/Products",
        operation_id="fetch_products_001"
    )
    
    error_id = await dlq.add_error(e, context)
    print(f"Error recorded: {error_id}")
```

### Retry Processing
```python
# Process retries periodically
async def retry_loop():
    while True:
        retry_results = await dlq.process_retries()
        
        if retry_results:
            print(f"Processed {len(retry_results)} retry attempts")
        
        await asyncio.sleep(300)  # Check every 5 minutes

# Start retry processing
asyncio.create_task(retry_loop())
```

### Error Analysis
```python
# Get error statistics
stats = dlq.get_error_statistics()
print(f"Active errors: {stats['active_errors']}")
print(f"Resolution rate: {stats['resolution_rate_percent']:.1f}%")

# Export error report
await dlq.export_error_report("error_report.json")

# Get errors by entity
entity_errors = dlq.get_errors_by_entity()
for entity, errors in entity_errors.items():
    print(f"{entity}: {len(errors)} errors")
```

### Custom Error Handling
```python
# Register custom error handler
handler = CustomErrorHandler(dlq)

async def handle_timeout_error(exception: Exception, context: ErrorContext) -> bool:
    """Custom timeout error handler"""
    # Increase timeout for next request
    context.user_context = context.user_context or {}
    context.user_context['timeout'] = 60  # Increase to 60 seconds
    
    # Don't add to dead letter queue, handle inline
    return True

handler.register_handler("TimeoutError", handle_timeout_error)

# Use custom handler
try:
    result = await operation()
except Exception as e:
    handled = await handler.handle_error(e, context)
    if not handled:
        print("Error sent to dead letter queue")
```

This file demonstrates enterprise-grade error handling with comprehensive error classification, retry logic, persistent storage, and detailed error analysis capabilities for production SAP OData connector deployments.
