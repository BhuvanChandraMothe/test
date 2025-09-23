"""Plan generator for SAP OData connector"""

import asyncio
from typing import Dict, List, Optional, Any, Iterator
from dataclasses import dataclass, field
from enum import Enum
import structlog
import math

logger = structlog.get_logger(__name__)


class CommandType(Enum):
    """Types of fetch commands"""
    FETCH_PAGE = "fetch_page"
    COUNT_RECORDS = "count_records"
    VALIDATE_SCHEMA = "validate_schema"


class Priority(Enum):
    """Command priority levels"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class FetchCommand:
    """Command to fetch data from SAP OData API"""
    command_id: str
    command_type: CommandType
    entity_set: str
    skip: int = 0
    top: int = 1000
    filter_clause: Optional[str] = None
    select_clause: Optional[str] = None
    orderby_clause: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    
    @property
    def url_params(self) -> Dict[str, str]:
        """Generate OData URL parameters"""
        params = {
            '$skip': str(self.skip),
            '$top': str(self.top)
        }
        
        if self.filter_clause:
            params['$filter'] = self.filter_clause
        
        if self.select_clause:
            params['$select'] = self.select_clause
        
        if self.orderby_clause:
            params['$orderby'] = self.orderby_clause
        
        return params
    
    def create_retry_command(self) -> 'FetchCommand':
        """Create a new command for retry with incremented retry count"""
        return FetchCommand(
            command_id=f"{self.command_id}_retry_{self.retry_count + 1}",
            command_type=self.command_type,
            entity_set=self.entity_set,
            skip=self.skip,
            top=self.top,
            filter_clause=self.filter_clause,
            select_clause=self.select_clause,
            orderby_clause=self.orderby_clause,
            priority=self.priority,
            retry_count=self.retry_count + 1,
            max_retries=self.max_retries
        )
    
    def can_retry(self) -> bool:
        """Check if command can be retried"""
        return self.retry_count < self.max_retries


@dataclass
class EntityPlan:
    """Execution plan for a single entity"""
    entity_name: str
    total_records: int
    page_size: int
    total_pages: int
    priority: Priority
    dependencies: List[str] = field(default_factory=list)
    commands: List[FetchCommand] = field(default_factory=list)
    
    def generate_commands(self) -> List[FetchCommand]:
        """Generate fetch commands for this entity"""
        commands = []
        
        # Generate page fetch commands
        for page_num in range(self.total_pages):
            skip = page_num * self.page_size
            command_id = f"{self.entity_name}_page_{page_num + 1}"
            
            command = FetchCommand(
                command_id=command_id,
                command_type=CommandType.FETCH_PAGE,
                entity_set=self.entity_name,
                skip=skip,
                top=self.page_size,
                priority=self.priority
            )
            commands.append(command)
        
        self.commands = commands
        return commands


class PlanGenerator:
    """Generates execution plans for SAP OData data fetching"""
    
    def __init__(self, batch_size: int = 1000, max_concurrent_entities: int = 5):
        self.batch_size = batch_size
        self.max_concurrent_entities = max_concurrent_entities
        self.entity_plans: Dict[str, EntityPlan] = {}
        self.processing_levels: List[List[str]] = []
    
    def create_execution_plan(
        self,
        entity_counts: Dict[str, int],
        processing_order: List[List[str]],
        selected_entities: Optional[List[str]] = None
    ) -> Dict[str, EntityPlan]:
        """Create comprehensive execution plan"""
        
        logger.info("Creating execution plan", 
                   total_entities=len(entity_counts),
                   selected_entities=len(selected_entities) if selected_entities else "all")
        
        self.processing_levels = processing_order
        
        # Filter entities if selection is provided
        if selected_entities:
            entity_counts = {k: v for k, v in entity_counts.items() if k in selected_entities}
        
        # Create plans for each entity
        for level_idx, level_entities in enumerate(processing_order):
            for entity in level_entities:
                if entity not in entity_counts:
                    continue
                
                record_count = entity_counts[entity]
                if record_count == 0:
                    logger.info("Skipping empty entity", entity=entity)
                    continue
                
                # Calculate pagination
                total_pages = math.ceil(record_count / self.batch_size)
                
                # Determine priority based on level and size
                priority = self._calculate_priority(level_idx, record_count)
                
                # Get dependencies from previous levels
                dependencies = []
                for prev_level in processing_order[:level_idx]:
                    dependencies.extend(prev_level)
                
                # Create entity plan
                plan = EntityPlan(
                    entity_name=entity,
                    total_records=record_count,
                    page_size=self.batch_size,
                    total_pages=total_pages,
                    priority=priority,
                    dependencies=dependencies
                )
                
                # Generate commands
                plan.generate_commands()
                self.entity_plans[entity] = plan
                
                logger.debug("Created plan for entity",
                           entity=entity,
                           records=record_count,
                           pages=total_pages,
                           priority=priority.name)
        
        logger.info("Execution plan created",
                   planned_entities=len(self.entity_plans),
                   total_commands=sum(len(plan.commands) for plan in self.entity_plans.values()))
        
        return self.entity_plans
    
    def _calculate_priority(self, level_idx: int, record_count: int) -> Priority:
        """Calculate priority based on dependency level and record count"""
        # Higher priority for entities with dependencies (lower levels)
        if level_idx == 0:
            return Priority.HIGH
        elif level_idx <= 2:
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def get_initial_commands(self) -> List[FetchCommand]:
        """Get initial batch of commands to start processing"""
        commands = []
        
        # Start with independent entities (level 0)
        if self.processing_levels:
            first_level_entities = self.processing_levels[0]
            
            for entity in first_level_entities:
                if entity in self.entity_plans:
                    plan = self.entity_plans[entity]
                    # Add first few commands for each entity
                    commands.extend(plan.commands[:min(3, len(plan.commands))])
        
        # Sort by priority
        commands.sort(key=lambda cmd: cmd.priority.value)
        
        logger.info("Generated initial commands", command_count=len(commands))
        return commands
    
    def get_next_commands(self, completed_entity: str) -> List[FetchCommand]:
        """Get next commands after an entity is completed"""
        commands = []
        
        # Find entities that depend on the completed entity
        for level in self.processing_levels:
            for entity in level:
                if entity in self.entity_plans:
                    plan = self.entity_plans[entity]
                    if completed_entity in plan.dependencies:
                        # This entity can now be processed
                        commands.extend(plan.commands[:min(3, len(plan.commands))])
        
        # Sort by priority
        commands.sort(key=lambda cmd: cmd.priority.value)
        
        logger.debug("Generated next commands",
                    completed_entity=completed_entity,
                    new_commands=len(commands))
        
        return commands
    
    def get_remaining_commands(self, entity: str, completed_pages: List[int]) -> List[FetchCommand]:
        """Get remaining commands for an entity after some pages are completed"""
        if entity not in self.entity_plans:
            return []
        
        plan = self.entity_plans[entity]
        remaining_commands = []
        
        for i, command in enumerate(plan.commands):
            page_num = i + 1
            if page_num not in completed_pages:
                remaining_commands.append(command)
        
        return remaining_commands
    
    def create_next_page_command(self, current_command: FetchCommand, next_link: str) -> FetchCommand:
        """Create command for next page based on OData next link"""
        # Parse skip value from next link
        import re
        skip_match = re.search(r'\$skip=(\d+)', next_link)
        new_skip = int(skip_match.group(1)) if skip_match else current_command.skip + current_command.top
        
        # Create new command
        next_command = FetchCommand(
            command_id=f"{current_command.entity_set}_page_next_{new_skip}",
            command_type=CommandType.FETCH_PAGE,
            entity_set=current_command.entity_set,
            skip=new_skip,
            top=current_command.top,
            filter_clause=current_command.filter_clause,
            select_clause=current_command.select_clause,
            orderby_clause=current_command.orderby_clause,
            priority=current_command.priority
        )
        
        return next_command
    
    def get_plan_summary(self) -> Dict[str, Any]:
        """Get summary of the execution plan"""
        total_commands = sum(len(plan.commands) for plan in self.entity_plans.values())
        total_records = sum(plan.total_records for plan in self.entity_plans.values())
        
        priority_breakdown = {
            Priority.HIGH.name: 0,
            Priority.MEDIUM.name: 0,
            Priority.LOW.name: 0
        }
        
        for plan in self.entity_plans.values():
            priority_breakdown[plan.priority.name] += len(plan.commands)
        
        return {
            'total_entities': len(self.entity_plans),
            'total_commands': total_commands,
            'total_records': total_records,
            'processing_levels': len(self.processing_levels),
            'priority_breakdown': priority_breakdown,
            'average_pages_per_entity': total_commands / len(self.entity_plans) if self.entity_plans else 0
        }
