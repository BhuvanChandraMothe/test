"""Dead Letter Queue implementation for failed commands"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import structlog
import orjson
from datetime import datetime, timezone

# Import at runtime to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from planning.plan_generator import FetchCommand

logger = structlog.get_logger(__name__)


class FailureType(Enum):
    """Types of failures that can occur"""
    PERMANENT_CLIENT_ERROR = "permanent_client_error"  # 4xx errors
    TRANSIENT_SERVER_ERROR = "transient_server_error"  # 5xx errors
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    CIRCUIT_BREAKER_ERROR = "circuit_breaker_error"
    TRANSFORMATION_ERROR = "transformation_error"
    STORAGE_ERROR = "storage_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class FailedCommand:
    """Represents a failed command in the dead letter queue"""
    
    command: 'FetchCommand'  # Forward reference to avoid circular import
    failure_type: FailureType
    error_message: str
    error_details: Dict[str, Any] = field(default_factory=dict)
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_attempts: int = 0
    last_retry_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'command': {
                'command_id': self.command.command_id,
                'command_type': self.command.command_type.value,
                'entity_set': self.command.entity_set,
                'skip': self.command.skip,
                'top': self.command.top,
                'filter_clause': self.command.filter_clause,
                'select_clause': self.command.select_clause,
                'orderby_clause': self.command.orderby_clause,
                'priority': self.command.priority.value,
                'retry_count': self.command.retry_count,
                'max_retries': self.command.max_retries
            },
            'failure_type': self.failure_type.value,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'failed_at': self.failed_at.isoformat(),
            'retry_attempts': self.retry_attempts,
            'last_retry_at': self.last_retry_at.isoformat() if self.last_retry_at else None
        }


class DeadLetterQueue:
    """Dead Letter Queue for handling permanently failed commands"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue: List[FailedCommand] = []
        self._lock = asyncio.Lock()
        self._stats = {
            'total_failures': 0,
            'failures_by_type': {},
            'failures_by_entity': {}
        }
    
    async def add_failed_command(
        self,
        command: 'FetchCommand',
        failure_type: FailureType,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ):
        """Add a failed command to the dead letter queue"""
        
        async with self._lock:
            failed_command = FailedCommand(
                command=command,
                failure_type=failure_type,
                error_message=error_message,
                error_details=error_details or {}
            )
            
            self._queue.append(failed_command)
            
            # Maintain max size
            if len(self._queue) > self.max_size:
                removed = self._queue.pop(0)
                logger.warning("DLQ at max capacity, removed oldest entry",
                             removed_command_id=removed.command.command_id)
            
            # Update statistics
            self._update_stats(failed_command)
            
            logger.error("Command added to dead letter queue",
                        command_id=command.command_id,
                        entity_set=command.entity_set,
                        failure_type=failure_type.value,
                        error_message=error_message)
    
    def _update_stats(self, failed_command: FailedCommand):
        """Update failure statistics"""
        self._stats['total_failures'] += 1
        
        # Update by failure type
        failure_type = failed_command.failure_type.value
        if failure_type not in self._stats['failures_by_type']:
            self._stats['failures_by_type'][failure_type] = 0
        self._stats['failures_by_type'][failure_type] += 1
        
        # Update by entity
        entity = failed_command.command.entity_set
        if entity not in self._stats['failures_by_entity']:
            self._stats['failures_by_entity'][entity] = 0
        self._stats['failures_by_entity'][entity] += 1
    
    async def get_failed_commands(
        self,
        failure_type: Optional[FailureType] = None,
        entity_set: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FailedCommand]:
        """Get failed commands with optional filtering"""
        
        async with self._lock:
            filtered_commands = self._queue.copy()
            
            if failure_type:
                filtered_commands = [
                    cmd for cmd in filtered_commands
                    if cmd.failure_type == failure_type
                ]
            
            if entity_set:
                filtered_commands = [
                    cmd for cmd in filtered_commands
                    if cmd.command.entity_set == entity_set
                ]
            
            if limit:
                filtered_commands = filtered_commands[:limit]
            
            return filtered_commands
    
    async def retry_failed_command(self, command_id: str) -> Optional['FetchCommand']:
        """Remove a command from DLQ for retry"""
        
        async with self._lock:
            for i, failed_command in enumerate(self._queue):
                if failed_command.command.command_id == command_id:
                    # Remove from DLQ
                    removed_command = self._queue.pop(i)
                    
                    # Update retry info
                    removed_command.retry_attempts += 1
                    removed_command.last_retry_at = datetime.now(timezone.utc)
                    
                    logger.info("Command removed from DLQ for retry",
                              command_id=command_id,
                              retry_attempts=removed_command.retry_attempts)
                    
                    return removed_command.command
            
            logger.warning("Command not found in DLQ", command_id=command_id)
            return None
    
    async def clear_failed_commands(
        self,
        failure_type: Optional[FailureType] = None,
        entity_set: Optional[str] = None
    ) -> int:
        """Clear failed commands with optional filtering"""
        
        async with self._lock:
            original_count = len(self._queue)
            
            if not failure_type and not entity_set:
                # Clear all
                self._queue.clear()
                cleared_count = original_count
            else:
                # Filter and remove
                new_queue = []
                for cmd in self._queue:
                    should_remove = True
                    
                    if failure_type and cmd.failure_type != failure_type:
                        should_remove = False
                    
                    if entity_set and cmd.command.entity_set != entity_set:
                        should_remove = False
                    
                    if not should_remove:
                        new_queue.append(cmd)
                
                cleared_count = len(self._queue) - len(new_queue)
                self._queue = new_queue
            
            logger.info("Cleared failed commands from DLQ",
                       cleared_count=cleared_count,
                       remaining_count=len(self._queue))
            
            return cleared_count
    
    async def export_failed_commands(self, file_path: str):
        """Export failed commands to JSON file"""
        
        async with self._lock:
            export_data = {
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'total_commands': len(self._queue),
                'statistics': self._stats,
                'failed_commands': [cmd.to_dict() for cmd in self._queue]
            }
            
            with open(file_path, 'wb') as f:
                f.write(orjson.dumps(export_data, option=orjson.OPT_INDENT_2))
            
            logger.info("Exported failed commands",
                       file_path=file_path,
                       command_count=len(self._queue))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        return {
            'current_size': len(self._queue),
            'max_size': self.max_size,
            'total_failures': self._stats['total_failures'],
            'failures_by_type': self._stats['failures_by_type'].copy(),
            'failures_by_entity': self._stats['failures_by_entity'].copy()
        }
    
    def is_full(self) -> bool:
        """Check if DLQ is at capacity"""
        return len(self._queue) >= self.max_size
    
    def is_empty(self) -> bool:
        """Check if DLQ is empty"""
        return len(self._queue) == 0


class ErrorClassifier:
    """Classifies errors to determine failure type"""
    
    @staticmethod
    def classify_http_error(status_code: int, error_message: str) -> FailureType:
        """Classify HTTP errors"""
        
        if status_code == 401 or status_code == 403:
            return FailureType.AUTHENTICATION_ERROR
        
        elif status_code == 429:
            return FailureType.RATE_LIMIT_ERROR
        
        elif 400 <= status_code < 500:
            return FailureType.PERMANENT_CLIENT_ERROR
        
        elif 500 <= status_code < 600:
            return FailureType.TRANSIENT_SERVER_ERROR
        
        else:
            return FailureType.UNKNOWN_ERROR
    
    @staticmethod
    def classify_exception(exception: Exception) -> FailureType:
        """Classify Python exceptions"""
        
        exception_name = type(exception).__name__
        error_message = str(exception).lower()
        
        if 'timeout' in error_message or 'timed out' in error_message:
            return FailureType.TIMEOUT_ERROR
        
        elif 'circuit' in error_message and 'breaker' in error_message:
            return FailureType.CIRCUIT_BREAKER_ERROR
        
        elif 'auth' in error_message or 'credential' in error_message:
            return FailureType.AUTHENTICATION_ERROR
        
        elif 'transform' in error_message or 'parse' in error_message:
            return FailureType.TRANSFORMATION_ERROR
        
        elif 'storage' in error_message or 'bigquery' in error_message or 'gcs' in error_message:
            return FailureType.STORAGE_ERROR
        
        else:
            return FailureType.UNKNOWN_ERROR
    
    @staticmethod
    def is_retryable(failure_type: FailureType) -> bool:
        """Determine if a failure type is retryable"""
        
        retryable_types = {
            FailureType.TRANSIENT_SERVER_ERROR,
            FailureType.TIMEOUT_ERROR,
            FailureType.RATE_LIMIT_ERROR,
            FailureType.CIRCUIT_BREAKER_ERROR,
            FailureType.STORAGE_ERROR
        }
        
        return failure_type in retryable_types
