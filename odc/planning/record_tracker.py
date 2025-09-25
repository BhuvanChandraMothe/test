"""Record tracking system to ensure accurate record counts"""

import asyncio
from typing import Dict, Set, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EntityRecordTracker:
    """Track records fetched for a single entity"""
    entity_name: str
    target_records: int
    records_fetched: int = 0
    pages_completed: Set[int] = None
    is_complete: bool = False
    
    def __post_init__(self):
        if self.pages_completed is None:
            self.pages_completed = set()
    
    def add_page_records(self, page_num: int, record_count: int) -> bool:
        """Add records from a completed page. Returns True if entity is now complete."""
        if page_num in self.pages_completed:
            logger.warning("Page already completed", 
                          entity=self.entity_name, 
                          page=page_num)
            return self.is_complete
        
        self.pages_completed.add(page_num)
        self.records_fetched += record_count
        
        # Check if we've reached the target
        if self.records_fetched >= self.target_records:
            self.is_complete = True
            logger.info("✅ Entity record fetching complete", 
                       entity=self.entity_name,
                       fetched=self.records_fetched,
                       target=self.target_records)
        
        return self.is_complete
    
    def should_fetch_more(self) -> bool:
        """Check if we should fetch more records for this entity"""
        return not self.is_complete and self.records_fetched < self.target_records
    
    def get_remaining_records(self) -> int:
        """Get number of records still needed"""
        return max(0, self.target_records - self.records_fetched)


class GlobalRecordTracker:
    """Global record tracker to coordinate between workers"""
    
    def __init__(self):
        self._entity_trackers: Dict[str, EntityRecordTracker] = {}
        self._lock = asyncio.Lock()
        self._total_records_limit: Optional[int] = None
        self._global_records_fetched = 0
    
    def set_total_records_limit(self, limit: Optional[int]):
        """Set global limit for total records across all entities"""
        self._total_records_limit = limit
        logger.info("Global record limit set", limit=limit)
    
    async def register_entity(self, entity_name: str, target_records: int):
        """Register an entity for tracking"""
        async with self._lock:
            # Apply global limit if set
            if self._total_records_limit:
                remaining_global = self._total_records_limit - self._global_records_fetched
                target_records = min(target_records, remaining_global)
            
            self._entity_trackers[entity_name] = EntityRecordTracker(
                entity_name=entity_name,
                target_records=target_records
            )
            
            logger.info("Entity registered for tracking", 
                       entity=entity_name,
                       target_records=target_records)
    
    async def record_page_completion(self, entity_name: str, page_num: int, record_count: int) -> Dict[str, bool]:
        """Record completion of a page. Returns status info."""
        async with self._lock:
            if entity_name not in self._entity_trackers:
                logger.error("Entity not registered for tracking", entity=entity_name)
                return {"entity_complete": False, "global_limit_reached": False}
            
            tracker = self._entity_trackers[entity_name]
            
            # Check global limit first
            if self._total_records_limit:
                if self._global_records_fetched >= self._total_records_limit:
                    logger.warning("Global record limit already reached", 
                                 limit=self._total_records_limit,
                                 fetched=self._global_records_fetched)
                    return {"entity_complete": True, "global_limit_reached": True}
                
                # Adjust record count if it would exceed global limit
                remaining_global = self._total_records_limit - self._global_records_fetched
                actual_records = min(record_count, remaining_global)
            else:
                actual_records = record_count
            
            # Update entity tracker
            entity_complete = tracker.add_page_records(page_num, actual_records)
            
            # Update global counter
            self._global_records_fetched += actual_records
            
            # Check if global limit is reached
            global_limit_reached = (
                self._total_records_limit and 
                self._global_records_fetched >= self._total_records_limit
            )
            
            if global_limit_reached:
                logger.info("🎯 Global record limit reached", 
                           limit=self._total_records_limit,
                           fetched=self._global_records_fetched)
                # Mark all entities as complete
                for t in self._entity_trackers.values():
                    t.is_complete = True
            
            return {
                "entity_complete": entity_complete,
                "global_limit_reached": global_limit_reached,
                "actual_records_added": actual_records,
                "entity_records_fetched": tracker.records_fetched,
                "global_records_fetched": self._global_records_fetched
            }
    
    async def should_create_more_commands(self, entity_name: str) -> bool:
        """Check if more commands should be created for an entity"""
        async with self._lock:
            if entity_name not in self._entity_trackers:
                return False
            
            tracker = self._entity_trackers[entity_name]
            
            # Check entity-specific limit
            if not tracker.should_fetch_more():
                return False
            
            # Check global limit
            if self._total_records_limit:
                if self._global_records_fetched >= self._total_records_limit:
                    return False
            
            return True
    
    async def get_entity_records_fetched(self, entity_name: str) -> int:
        """Get the number of records fetched for a specific entity."""
        async with self._lock:
            if entity_name in self._entity_trackers:
                return self._entity_trackers[entity_name].records_fetched
            return 0
    
    async def get_entity_status(self, entity_name: str) -> Optional[Dict[str, any]]:
        """Get status for a specific entity"""
        async with self._lock:
            if entity_name not in self._entity_trackers:
                return None
            
            tracker = self._entity_trackers[entity_name]
            return {
                "entity_name": tracker.entity_name,
                "target_records": tracker.target_records,
                "records_fetched": tracker.records_fetched,
                "pages_completed": len(tracker.pages_completed),
                "is_complete": tracker.is_complete,
                "remaining_records": tracker.get_remaining_records()
            }
    
    async def get_global_status(self) -> Dict[str, any]:
        """Get global tracking status"""
        async with self._lock:
            entity_statuses = {}
            for entity_name in self._entity_trackers:
                entity_statuses[entity_name] = await self.get_entity_status(entity_name)
            
            return {
                "total_records_limit": self._total_records_limit,
                "global_records_fetched": self._global_records_fetched,
                "entities_tracked": len(self._entity_trackers),
                "entities_complete": sum(1 for t in self._entity_trackers.values() if t.is_complete),
                "entity_statuses": entity_statuses
            }
    
    async def calculate_optimal_batch_size(self, entity_name: str, default_batch_size: int) -> int:
        """Calculate optimal batch size to avoid overfetching"""
        async with self._lock:
            if entity_name not in self._entity_trackers:
                return default_batch_size
            
            tracker = self._entity_trackers[entity_name]
            remaining_entity = tracker.get_remaining_records()
            
            # Consider global limit
            if self._total_records_limit:
                remaining_global = self._total_records_limit - self._global_records_fetched
                remaining = min(remaining_entity, remaining_global)
            else:
                remaining = remaining_entity
            
            # Return smaller of default batch size or remaining records
            optimal_size = min(default_batch_size, remaining)
            
            if optimal_size != default_batch_size:
                logger.info("Adjusted batch size to prevent overfetching",
                           entity=entity_name,
                           default_size=default_batch_size,
                           optimal_size=optimal_size,
                           remaining_records=remaining)
            
            return max(1, optimal_size)  # Ensure at least 1 record per batch


# Global instance
_global_tracker: Optional[GlobalRecordTracker] = None


def get_global_tracker() -> GlobalRecordTracker:
    """Get or create the global record tracker instance"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = GlobalRecordTracker()
    return _global_tracker


def reset_global_tracker():
    """Reset the global tracker (useful for testing)"""
    global _global_tracker
    _global_tracker = GlobalRecordTracker()
