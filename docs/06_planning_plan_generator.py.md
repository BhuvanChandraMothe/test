# planning/plan_generator.py - Plan Generator Documentation

## Overview
The `planning/plan_generator.py` file implements the execution planning system for the SAP OData Connector. It creates optimized fetch commands based on entity counts, dependencies, and processing constraints.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog

from services.metadata import EntitySchema
```

**Library Concepts:**
- **dataclasses**: Modern Python data containers with automatic methods
- **enum**: Type-safe enumeration for command priorities
- **typing**: Advanced type hints for complex data structures
- **structlog**: Structured logging for plan generation tracking

### Command Priority Enumeration
```python
class CommandPriority(Enum):
    """Priority levels for fetch commands"""
    CRITICAL = 1    # Dependencies for other entities
    HIGH = 2        # Large entities that should start early
    MEDIUM = 3      # Regular entities
    LOW = 4         # Small entities that can wait
```

**Enumeration Design Patterns:**
- **Semantic naming**: Priority levels have business meaning
- **Numeric values**: Lower numbers = higher priority
- **Extensibility**: Easy to add new priority levels
- **Type safety**: Prevents invalid priority assignments

### FetchCommand Data Class
```python
@dataclass
class FetchCommand:
    """Represents a single data fetch operation"""
    
    entity_name: str
    entity_set: str
    skip: int = 0
    top: int = 1000
    priority: CommandPriority = CommandPriority.MEDIUM
    dependencies: Set[str] = field(default_factory=set)
    estimated_records: int = 0
    batch_id: str = ""
    
    def __post_init__(self):
        """Validate command parameters after initialization"""
        if self.top <= 0:
            raise ValueError("top must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        
        # Generate batch ID if not provided
        if not self.batch_id:
            self.batch_id = f"{self.entity_name}_{self.skip}_{self.top}"
```

**Data Class Concepts:**
- **Automatic methods**: `__init__`, `__repr__`, `__eq__` generated automatically
- **Default factories**: `field(default_factory=set)` creates new set for each instance
- **Post-initialization**: `__post_init__` for validation and computed fields
- **Immutable by default**: Can add `frozen=True` for immutability
- **Type hints**: All fields have explicit types

### EntityPlan Data Class
```python
@dataclass
class EntityPlan:
    """Complete execution plan for a single entity"""
    
    entity_name: str
    total_records: int
    commands: List[FetchCommand] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    priority: CommandPriority = CommandPriority.MEDIUM
    
    @property
    def total_batches(self) -> int:
        """Calculate total number of batches"""
        return len(self.commands)
    
    @property
    def estimated_duration(self) -> float:
        """Estimate processing duration in seconds"""
        # Rough estimate: 1 second per 1000 records
        return self.total_records / 1000.0
    
    def add_command(self, command: FetchCommand) -> None:
        """Add a fetch command to this plan"""
        command.priority = self.priority  # Inherit entity priority
        self.commands.append(command)
```

**Computed Properties Pattern:**
- **@property**: Make methods accessible as attributes
- **Derived data**: Calculate values from existing fields
- **Encapsulation**: Hide calculation logic
- **Performance**: Properties calculated on-demand

### PlanGenerator Class Structure
```python
class PlanGenerator:
    """Generates optimized execution plans for OData entities"""
    
    def __init__(self, batch_size: int = 1000, max_concurrent_entities: int = 5):
        self.batch_size = batch_size
        self.max_concurrent_entities = max_concurrent_entities
        self.logger = structlog.get_logger(__name__)
        
        # Planning parameters
        self.large_entity_threshold = 10000  # Records
        self.small_entity_threshold = 100    # Records
```

**Configuration-Driven Design:**
- **Parameterized behavior**: Batch size and concurrency configurable
- **Threshold-based logic**: Different strategies for different entity sizes
- **Logging integration**: Structured logging for plan generation
- **Extensible**: Easy to add new planning parameters

### Main Plan Generation Method
```python
async def generate_plan(
    self, 
    entity_counts: Dict[str, int], 
    schemas: Dict[str, EntitySchema],
    selected_entities: Optional[List[str]] = None
) -> List[EntityPlan]:
    """Generate complete execution plan for all entities"""
    
    self.logger.info("Starting plan generation", 
                     total_entities=len(entity_counts),
                     selected_entities=len(selected_entities) if selected_entities else "all")
    
    # Filter entities if selection provided
    if selected_entities:
        entity_counts = {k: v for k, v in entity_counts.items() if k in selected_entities}
    
    # Generate individual entity plans
    entity_plans = []
    for entity_name, count in entity_counts.items():
        schema = schemas.get(entity_name)
        if schema:
            plan = await self._create_entity_plan(entity_name, count, schema)
            entity_plans.append(plan)
    
    # Optimize plan order based on dependencies and priorities
    optimized_plans = self._optimize_execution_order(entity_plans, schemas)
    
    self.logger.info("Plan generation completed", 
                     total_plans=len(optimized_plans),
                     total_commands=sum(len(plan.commands) for plan in optimized_plans))
    
    return optimized_plans
```

**Plan Generation Flow:**
1. **Entity filtering**: Process only selected entities if specified
2. **Individual planning**: Create plan for each entity
3. **Dependency analysis**: Consider relationships between entities
4. **Order optimization**: Arrange for optimal execution
5. **Validation**: Ensure plan is executable

### Entity Plan Creation
```python
async def _create_entity_plan(self, entity_name: str, record_count: int, schema: EntitySchema) -> EntityPlan:
    """Create execution plan for a single entity"""
    
    # Determine priority based on entity characteristics
    priority = self._calculate_priority(entity_name, record_count, schema)
    
    # Extract dependencies from schema
    dependencies = set(schema.foreign_keys.values()) if hasattr(schema, 'foreign_keys') else set()
    
    # Create entity plan
    plan = EntityPlan(
        entity_name=entity_name,
        total_records=record_count,
        dependencies=dependencies,
        priority=priority
    )
    
    # Generate fetch commands (pagination)
    if record_count > 0:
        num_batches = (record_count + self.batch_size - 1) // self.batch_size  # Ceiling division
        
        for batch_num in range(num_batches):
            skip = batch_num * self.batch_size
            top = min(self.batch_size, record_count - skip)  # Handle last batch
            
            command = FetchCommand(
                entity_name=entity_name,
                entity_set=entity_name,  # Assuming entity set name matches entity name
                skip=skip,
                top=top,
                priority=priority,
                dependencies=dependencies.copy(),
                estimated_records=top
            )
            
            plan.add_command(command)
    
    return plan
```

**Pagination Logic:**
- **Ceiling division**: `(count + batch_size - 1) // batch_size` handles remainders
- **Skip/Top pattern**: OData pagination using `$skip` and `$top`
- **Last batch handling**: Ensure last batch doesn't exceed remaining records
- **Command generation**: Create individual fetch commands for each page

### Priority Calculation
```python
def _calculate_priority(self, entity_name: str, record_count: int, schema: EntitySchema) -> CommandPriority:
    """Calculate processing priority for an entity"""
    
    # Critical: Entities that other entities depend on
    if self._is_referenced_by_others(entity_name, schema):
        return CommandPriority.CRITICAL
    
    # High: Large entities that should start early
    if record_count > self.large_entity_threshold:
        return CommandPriority.HIGH
    
    # Low: Small entities that can wait
    if record_count < self.small_entity_threshold:
        return CommandPriority.LOW
    
    # Medium: Everything else
    return CommandPriority.MEDIUM

def _is_referenced_by_others(self, entity_name: str, schema: EntitySchema) -> bool:
    """Check if this entity is referenced by foreign keys in other entities"""
    # This would need access to all schemas to check foreign key references
    # Simplified implementation - could be enhanced with full dependency graph
    return entity_name.lower() in ['categories', 'suppliers', 'customers']  # Common parent entities
```

**Priority Assignment Strategy:**
- **Dependency-driven**: Parent entities get highest priority
- **Size-based**: Large entities start early to maximize parallelism
- **Resource optimization**: Small entities can fill gaps in processing
- **Business logic**: Domain-specific priority rules

### Execution Order Optimization
```python
def _optimize_execution_order(self, plans: List[EntityPlan], schemas: Dict[str, EntitySchema]) -> List[EntityPlan]:
    """Optimize the execution order of entity plans"""
    
    # Sort by priority first, then by estimated duration (descending)
    def sort_key(plan: EntityPlan) -> tuple:
        return (
            plan.priority.value,           # Lower number = higher priority
            -plan.estimated_duration,      # Negative for descending order (longer first)
            plan.entity_name              # Alphabetical for consistency
        )
    
    sorted_plans = sorted(plans, key=sort_key)
    
    # Apply dependency constraints
    optimized_plans = self._resolve_dependencies(sorted_plans)
    
    return optimized_plans

def _resolve_dependencies(self, plans: List[EntityPlan]) -> List[EntityPlan]:
    """Ensure dependent entities are processed after their dependencies"""
    
    resolved = []
    remaining = plans.copy()
    entity_names = {plan.entity_name for plan in plans}
    
    while remaining:
        # Find entities with no unresolved dependencies
        ready = []
        for plan in remaining:
            # Check if all dependencies are already resolved or not in our entity set
            deps_satisfied = all(
                dep in [p.entity_name for p in resolved] or dep not in entity_names
                for dep in plan.dependencies
            )
            if deps_satisfied:
                ready.append(plan)
        
        if not ready:
            # Circular dependency or missing dependency - take first remaining
            self.logger.warning("Potential circular dependency detected", 
                              remaining_entities=[p.entity_name for p in remaining])
            ready = [remaining[0]]
        
        # Move ready plans to resolved list
        for plan in ready:
            resolved.append(plan)
            remaining.remove(plan)
    
    return resolved
```

**Dependency Resolution Algorithm:**
- **Topological sorting**: Ensure dependencies processed before dependents
- **Multi-criteria sorting**: Priority, duration, and name for deterministic ordering
- **Circular dependency detection**: Handle edge cases gracefully
- **Partial dependency handling**: Allow processing when some dependencies are external

### Command Batching and Grouping
```python
def group_commands_by_priority(self, plans: List[EntityPlan]) -> Dict[CommandPriority, List[FetchCommand]]:
    """Group all commands by priority for execution scheduling"""
    
    groups = {priority: [] for priority in CommandPriority}
    
    for plan in plans:
        for command in plan.commands:
            groups[command.priority].append(command)
    
    return groups

def create_execution_batches(self, plans: List[EntityPlan], max_concurrent: int) -> List[List[FetchCommand]]:
    """Create batches of commands that can be executed concurrently"""
    
    all_commands = []
    for plan in plans:
        all_commands.extend(plan.commands)
    
    # Sort commands by priority
    all_commands.sort(key=lambda cmd: (cmd.priority.value, cmd.entity_name, cmd.skip))
    
    # Create batches respecting concurrency limits
    batches = []
    current_batch = []
    
    for command in all_commands:
        if len(current_batch) >= max_concurrent:
            batches.append(current_batch)
            current_batch = []
        current_batch.append(command)
    
    if current_batch:
        batches.append(current_batch)
    
    return batches
```

**Batch Processing Concepts:**
- **Priority grouping**: Separate commands by execution priority
- **Concurrency batching**: Limit simultaneous operations
- **Load balancing**: Distribute work across available workers
- **Sequential batches**: Process high-priority batches before low-priority

## Advanced Planning Concepts

### Dynamic Batch Size Adjustment
```python
def _calculate_optimal_batch_size(self, entity_name: str, record_count: int) -> int:
    """Calculate optimal batch size based on entity characteristics"""
    
    base_batch_size = self.batch_size
    
    # Adjust for very large entities
    if record_count > 100000:
        return min(base_batch_size * 2, 5000)  # Larger batches for big entities
    
    # Adjust for small entities
    if record_count < 1000:
        return min(base_batch_size, record_count)  # Don't over-batch small entities
    
    return base_batch_size
```

### Memory-Aware Planning
```python
def _estimate_memory_usage(self, plans: List[EntityPlan]) -> Dict[str, float]:
    """Estimate memory usage for each entity plan"""
    
    memory_estimates = {}
    
    for plan in plans:
        # Rough estimate: 1KB per record on average
        estimated_mb = (plan.total_records * 1024) / (1024 * 1024)
        memory_estimates[plan.entity_name] = estimated_mb
    
    return memory_estimates
```

### Adaptive Planning
```python
class AdaptivePlanGenerator(PlanGenerator):
    """Plan generator that adapts based on execution feedback"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_history = {}
    
    def update_from_execution(self, entity_name: str, actual_duration: float, actual_records: int):
        """Update planning parameters based on actual execution results"""
        
        if entity_name not in self.execution_history:
            self.execution_history[entity_name] = []
        
        self.execution_history[entity_name].append({
            'duration': actual_duration,
            'records': actual_records,
            'throughput': actual_records / actual_duration if actual_duration > 0 else 0
        })
    
    def _calculate_priority(self, entity_name: str, record_count: int, schema: EntitySchema) -> CommandPriority:
        """Enhanced priority calculation using execution history"""
        
        base_priority = super()._calculate_priority(entity_name, record_count, schema)
        
        # Adjust based on historical performance
        if entity_name in self.execution_history:
            history = self.execution_history[entity_name]
            avg_throughput = sum(h['throughput'] for h in history) / len(history)
            
            # Slow entities get higher priority to start earlier
            if avg_throughput < 100:  # records per second
                if base_priority == CommandPriority.MEDIUM:
                    return CommandPriority.HIGH
        
        return base_priority
```

## Key Programming Concepts

### 1. **Dataclass Design Patterns**
```python
@dataclass
class FetchCommand:
    # Required fields
    entity_name: str
    entity_set: str
    
    # Optional fields with defaults
    skip: int = 0
    top: int = 1000
    
    # Complex defaults
    dependencies: Set[str] = field(default_factory=set)
    
    # Validation
    def __post_init__(self):
        if self.top <= 0:
            raise ValueError("top must be positive")
```

### 2. **Enum-based Priority System**
```python
class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

# Usage
command.priority = Priority.HIGH
if command.priority.value < Priority.MEDIUM.value:
    # Higher priority
    pass
```

### 3. **Dependency Resolution Algorithm**
```python
def topological_sort(items, dependencies):
    resolved = []
    remaining = items.copy()
    
    while remaining:
        # Find items with no unresolved dependencies
        ready = [item for item in remaining 
                if all(dep in resolved for dep in dependencies.get(item, []))]
        
        if not ready:
            # Circular dependency
            break
            
        resolved.extend(ready)
        for item in ready:
            remaining.remove(item)
    
    return resolved
```

### 4. **Ceiling Division for Pagination**
```python
# Calculate number of pages needed
total_records = 2500
page_size = 1000
pages = (total_records + page_size - 1) // page_size  # = 3 pages

# Generate page commands
for page in range(pages):
    skip = page * page_size
    top = min(page_size, total_records - skip)
    # Create command with skip and top
```

## Usage Examples

### Basic Plan Generation
```python
from planning.plan_generator import PlanGenerator

generator = PlanGenerator(batch_size=1000, max_concurrent_entities=5)

plans = await generator.generate_plan(
    entity_counts={"Products": 77, "Categories": 8, "Orders": 830},
    schemas=metadata_schemas,
    selected_entities=["Products", "Orders"]
)

for plan in plans:
    print(f"{plan.entity_name}: {plan.total_batches} batches, "
          f"priority {plan.priority.name}")
```

### Custom Priority Logic
```python
class CustomPlanGenerator(PlanGenerator):
    def _calculate_priority(self, entity_name: str, record_count: int, schema: EntitySchema) -> CommandPriority:
        # Custom business logic
        if entity_name in ["MasterData", "ReferenceData"]:
            return CommandPriority.CRITICAL
        elif "Transaction" in entity_name:
            return CommandPriority.HIGH
        else:
            return super()._calculate_priority(entity_name, record_count, schema)
```

### Execution Batch Creation
```python
generator = PlanGenerator()
plans = await generator.generate_plan(entity_counts, schemas)

# Create execution batches
batches = generator.create_execution_batches(plans, max_concurrent=3)

for i, batch in enumerate(batches):
    print(f"Batch {i+1}: {len(batch)} commands")
    for cmd in batch:
        print(f"  {cmd.entity_name}[{cmd.skip}:{cmd.skip+cmd.top}]")
```

This file demonstrates sophisticated execution planning with dependency resolution, priority management, and adaptive optimization strategies.
