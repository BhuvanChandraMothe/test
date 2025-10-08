import asyncio
from typing import Dict, List, Optional, Any, Iterator
from dataclasses import dataclass, field
from enum import Enum
import structlog
import math

from .record_tracker import get_global_tracker

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
    """Command to fetch data from SAP OData API with full OData query support"""
    command_id: str
    command_type: CommandType
    entity_set: str
    skip: int = 0
    top: int = 1000
    filter_clause: Optional[str] = None
    select_clause: Optional[str] = None
    orderby_clause: Optional[str] = None
    expand_clause: Optional[str] = None
    groupby_clause: Optional[str] = None
    aggregate_clause: Optional[str] = None
    count_option: bool = False
    search_clause: Optional[str] = None
    custom_params: Optional[Dict[str, str]] = None
    priority: Priority = Priority.MEDIUM
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    
    @property
    def url_params(self) -> Dict[str, str]:
        """Generate comprehensive OData URL parameters"""
        params = {
            '$skip': str(self.skip),
            '$top': str(self.top)
        }
        
        # Standard OData query options
        if self.filter_clause:
            params['$filter'] = self.filter_clause
        
        if self.select_clause:
            params['$select'] = self.select_clause
        
        if self.orderby_clause:
            params['$orderby'] = self.orderby_clause
        
        if self.expand_clause:
            params['$expand'] = self.expand_clause
        
        if self.search_clause:
            params['$search'] = self.search_clause
        
        if self.count_option:
            params['$count'] = 'true'
        
        # Advanced aggregation support (OData v4)
        if self.groupby_clause:
            params['$apply'] = f"groupby(({self.groupby_clause}))"
            
        if self.aggregate_clause:
            if '$apply' in params:
                # Combine with existing groupby
                params['$apply'] += f",aggregate({self.aggregate_clause})"
            else:
                params['$apply'] = f"aggregate({self.aggregate_clause})"
        
        # Custom parameters (for SAP-specific extensions)
        if self.custom_params:
            params.update(self.custom_params)
        
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
            expand_clause=self.expand_clause,
            groupby_clause=self.groupby_clause,
            aggregate_clause=self.aggregate_clause,
            count_option=self.count_option,
            search_clause=self.search_clause,
            custom_params=self.custom_params.copy() if self.custom_params else None,
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
    filter_clause: Optional[str] = field(default=None)
    
    def generate_commands(self) -> List[FetchCommand]:
        """Generate fetch commands for this entity"""
        commands = []
        
        # Calculate the number of pages needed
        total_records = self.total_records
        page_size = self.page_size
        
        if total_records > 0:
            for i in range(0, total_records, page_size):
                skip = i
                top = min(page_size, total_records - i)
                command_id = f"{self.entity_name}_page_{i // page_size + 1}"
                
                command = FetchCommand(
                    command_id=command_id,
                    command_type=CommandType.FETCH_PAGE,
                    entity_set=self.entity_name,
                    skip=skip,
                    top=top,
                    filter_clause=self.filter_clause,
                    priority=self.priority
                )
                commands.append(command)
        
        self.commands = commands
        return commands
    
    def generate_commands_with_filter(self, filter_condition: Optional[str] = None) -> List[FetchCommand]:
        """Generate fetch commands for this entity with optional filtering"""
        commands = []
        
        # Calculate the number of pages needed
        total_records = self.total_records
        page_size = self.page_size
        
        if total_records > 0:
            for i in range(0, total_records, page_size):
                skip = i
                top = min(page_size, total_records - i)
                command_id = f"{self.entity_name}_filtered_page_{i // page_size + 1}"
                
                command = FetchCommand(
                    command_id=command_id,
                    command_type=CommandType.FETCH_PAGE,
                    entity_set=self.entity_name,
                    skip=skip,
                    top=top,
                    filter_clause=filter_condition,
                    priority=self.priority
                )
                commands.append(command)
        
        self.commands = commands
        return commands


class PlanGenerator:
    """Generates execution plans for SAP OData data fetching"""
    
    def __init__(self, batch_size: int = 1000, max_concurrent_entities: int = 5, total_records_limit: Optional[int] = None):
        self.batch_size = batch_size
        self.max_concurrent_entities = max_concurrent_entities
        self.total_records_limit = total_records_limit
        self.entity_plans: Dict[str, EntityPlan] = {}
        self.processing_levels: List[List[str]] = []
        self.record_tracker = get_global_tracker()
        
        # Set global limit in tracker
        if total_records_limit:
            self.record_tracker.set_total_records_limit(total_records_limit)
    
    async def create_execution_plan(
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
                
                # Apply total records limit if set
                if self.total_records_limit:
                    # Calculate how many records we can still fetch globally
                    # This is a rough estimate - the record tracker will handle precise limits
                    record_count = min(record_count, self.total_records_limit)
                
                # Register entity with record tracker
                await self.record_tracker.register_entity(entity, record_count)
                
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
    
    async def create_execution_plan_filtered(
        self,
        entity_counts: Dict[str, int],
        processing_order: List[List[str]],
        selected_entities: List[str],
        filter_condition: Optional[str] = None
    ) -> Dict[str, EntityPlan]:
        """Create execution plan with filtering support"""
        
        logger.info("Creating filtered execution plan", 
                   total_entities=len(selected_entities),
                   filter_condition=filter_condition)
        
        self.processing_levels = processing_order
        
        # Filter entity counts to only selected entities
        filtered_counts = {k: v for k, v in entity_counts.items() if k in selected_entities}
        
        # Create plans for each selected entity
        for level_idx, level_entities in enumerate(processing_order):
            for entity in level_entities:
                if entity not in selected_entities or entity not in filtered_counts:
                    continue
                
                record_count = filtered_counts[entity]
                
                # Register entity with record tracker
                await self.record_tracker.register_entity(entity, record_count)
                
                # Calculate pagination
                total_pages = math.ceil(record_count / self.batch_size) if record_count > 0 else 1
                
                # Determine priority based on level and size
                priority = self._calculate_priority(level_idx, record_count)
                
                # Get dependencies from previous levels (only selected ones)
                dependencies = []
                for prev_level in processing_order[:level_idx]:
                    dependencies.extend([e for e in prev_level if e in selected_entities])
                
                # Create entity plan with filter
                plan = EntityPlan(
                    entity_name=entity,
                    total_records=record_count,
                    page_size=self.batch_size,
                    total_pages=total_pages,
                    priority=priority,
                    dependencies=dependencies,
                    filter_clause=filter_condition  # Add filter to the plan
                )
                
                # Generate commands (filter is already set in the plan)
                plan.generate_commands()
                self.entity_plans[entity] = plan
                
                logger.debug("Created filtered plan for entity",
                           entity=entity,
                           records=record_count,
                           pages=total_pages,
                           priority=priority.name,
                           filter=filter_condition)
        
        logger.info("Filtered execution plan created",
                   planned_entities=len(self.entity_plans),
                   total_commands=sum(len(plan.commands) for plan in self.entity_plans.values()),
                   filter_applied=bool(filter_condition))
        
        return self.entity_plans
    
    async def create_execution_plan_with_query_options(
        self,
        entity_counts: Dict[str, int],
        processing_order: List[List[str]],
        selected_entities: List[str],
        query_options: Dict[str, Any]
    ) -> Dict[str, EntityPlan]:
        """Create execution plan with comprehensive query options support"""
        
        logger.info("Creating execution plan with query options", 
                   total_entities=len(selected_entities),
                   query_options=query_options)
        
        self.processing_levels = processing_order
        
        # Extract query options
        filter_condition = query_options.get('filter_condition')
        select_fields = query_options.get('select_fields')
        expand_relations = query_options.get('expand_relations')
        order_by = query_options.get('order_by')
        group_by = query_options.get('group_by')
        aggregate_functions = query_options.get('aggregate_functions')
        search_query = query_options.get('search_query')
        include_count = query_options.get('include_count', False)
        custom_params = query_options.get('custom_query_params', {})
        
        for level_idx, level_entities in enumerate(processing_order):
            for entity_name in level_entities:
                if entity_name not in selected_entities:
                    continue
                
                record_count = entity_counts.get(entity_name, 0)
                
                # Calculate pages and priority
                total_pages = max(1, math.ceil(record_count / self.batch_size))
                priority = self._calculate_priority(record_count, level_idx)
                
                # Determine dependencies
                dependencies = []
                if level_idx > 0:
                    for prev_level in processing_order[:level_idx]:
                        dependencies.extend([e for e in prev_level if e in selected_entities])
                
                # Create entity plan with query options
                plan = EntityPlan(
                    entity_name=entity_name,
                    total_records=record_count,
                    page_size=self.batch_size,
                    total_pages=total_pages,
                    priority=priority,
                    dependencies=dependencies,
                    filter_clause=filter_condition
                )
                
                # Generate commands with enhanced query options
                commands = []
                for i in range(0, record_count, self.batch_size):
                    skip = i
                    top = min(self.batch_size, record_count - i)
                    command_id = f"{entity_name}_enhanced_page_{i // self.batch_size + 1}"
                    
                    command = FetchCommand(
                        command_id=command_id,
                        command_type=CommandType.FETCH_PAGE,
                        entity_set=entity_name,
                        skip=skip,
                        top=top,
                        filter_clause=filter_condition,
                        select_clause=select_fields,
                        orderby_clause=order_by,
                        expand_clause=expand_relations,
                        groupby_clause=group_by,
                        aggregate_clause=aggregate_functions,
                        count_option=include_count,
                        search_clause=search_query,
                        custom_params=custom_params.copy() if custom_params else None,
                        priority=priority
                    )
                    commands.append(command)
                
                plan.commands = commands
                self.entity_plans[entity_name] = plan
                
                logger.info(f"Created enhanced plan for {entity_name}",
                           records=record_count,
                           pages=total_pages,
                           priority=priority.name,
                           query_options_applied=len([opt for opt in query_options.values() if opt]))
        
        logger.info("Enhanced execution plan created",
                   planned_entities=len(self.entity_plans),
                   total_commands=sum(len(plan.commands) for plan in self.entity_plans.values()),
                   query_options_count=len([opt for opt in query_options.values() if opt]))
        
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
            
    def get_all_commands(self) -> List[FetchCommand]:
        """Get a combined list of all commands from all entity plans."""
        all_commands = []
        for plan in self.entity_plans.values():
            all_commands.extend(plan.commands)
        
        # Sort by priority
        all_commands.sort(key=lambda cmd: cmd.priority.value)
        
        logger.info("Generated a combined list of all commands", command_count=len(all_commands))
        return all_commands
    
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