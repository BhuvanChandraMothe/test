"""Relation graph builder for SAP OData connector"""

from typing import Dict, List, Set, Optional, Tuple
import networkx as nx
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class EntityRelation:
    """Represents a relationship between two entities"""
    from_entity: str
    to_entity: str
    from_property: str
    to_property: str
    relationship_type: str = "foreign_key"


class RelationGraphBuilder:
    """Builds dependency graph of entities based on foreign key relationships"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.relationships: List[EntityRelation] = []
    
    def add_entities(self, entity_names: List[str]):
        """Add entity nodes to the graph"""
        for entity in entity_names:
            self.graph.add_node(entity)
        logger.info("Added entities to graph", entity_count=len(entity_names))
    
    def add_relationships(self, relationships: Dict[str, List[Dict[str, str]]]):
        """Add foreign key relationships to the graph"""
        for entity, entity_relationships in relationships.items():
            for rel in entity_relationships:
                relation = EntityRelation(
                    from_entity=rel['from_entity'],
                    to_entity=rel['to_entity'],
                    from_property=rel['from_property'],
                    to_property=rel['to_property']
                )
                
                self.relationships.append(relation)
                
                # Add edge from dependent to principal (dependency direction)
                self.graph.add_edge(relation.from_entity, relation.to_entity, **{
                    'from_property': relation.from_property,
                    'to_property': relation.to_property,
                    'type': 'dependency'
                })
        
        logger.info("Added relationships to graph", relationship_count=len(self.relationships))
    
    def get_processing_order(self) -> List[List[str]]:
        """Get entities grouped by processing order (topological sort)"""
        try:
            # Check for cycles
            if not nx.is_directed_acyclic_graph(self.graph):
                cycles = list(nx.simple_cycles(self.graph))
                logger.warning("Circular dependencies detected", cycles=cycles)
                # Break cycles by removing some edges
                self._break_cycles()
            
            # Perform topological sort
            topo_order = list(nx.topological_sort(self.graph))
            
            # Group entities by dependency level
            levels = self._group_by_dependency_level(topo_order)
            
            logger.info("Generated processing order", levels=len(levels), total_entities=len(topo_order))
            return levels
            
        except nx.NetworkXError as e:
            logger.error("Failed to generate processing order", error=str(e))
            # Fallback: return all entities in a single group
            return [list(self.graph.nodes())]
    
    def _break_cycles(self):
        """Break circular dependencies by removing edges with lowest priority"""
        cycles = list(nx.simple_cycles(self.graph))
        
        for cycle in cycles:
            # Find the edge to remove (prefer removing self-references first)
            edge_to_remove = None
            
            for i in range(len(cycle)):
                from_node = cycle[i]
                to_node = cycle[(i + 1) % len(cycle)]
                
                if from_node == to_node:
                    # Self-reference, remove it
                    edge_to_remove = (from_node, to_node)
                    break
            
            if not edge_to_remove:
                # Remove the first edge in the cycle
                edge_to_remove = (cycle[0], cycle[1])
            
            if self.graph.has_edge(*edge_to_remove):
                self.graph.remove_edge(*edge_to_remove)
                logger.info("Removed edge to break cycle", edge=edge_to_remove)
    
    def _group_by_dependency_level(self, topo_order: List[str]) -> List[List[str]]:
        """Group entities by their dependency level for parallel processing"""
        levels = []
        remaining_nodes = set(topo_order)
        
        while remaining_nodes:
            # Find nodes with no dependencies among remaining nodes
            current_level = []
            
            for node in list(remaining_nodes):
                predecessors = set(self.graph.predecessors(node))
                if not predecessors.intersection(remaining_nodes):
                    current_level.append(node)
            
            if not current_level:
                # This shouldn't happen with a proper DAG, but handle it
                current_level = [remaining_nodes.pop()]
            else:
                for node in current_level:
                    remaining_nodes.remove(node)
            
            levels.append(current_level)
        
        return levels
    
    def get_dependencies(self, entity: str) -> List[str]:
        """Get direct dependencies for an entity"""
        return list(self.graph.predecessors(entity))
    
    def get_dependents(self, entity: str) -> List[str]:
        """Get entities that depend on this entity"""
        return list(self.graph.successors(entity))
    
    def is_independent(self, entity: str) -> bool:
        """Check if entity has no dependencies"""
        return len(list(self.graph.predecessors(entity))) == 0
    
    def get_relationship_info(self, from_entity: str, to_entity: str) -> Optional[Dict[str, str]]:
        """Get relationship information between two entities"""
        if self.graph.has_edge(from_entity, to_entity):
            return self.graph[from_entity][to_entity]
        return None
    
    def visualize_graph(self) -> str:
        """Generate a text representation of the dependency graph"""
        lines = ["Entity Dependency Graph:"]
        lines.append("=" * 30)
        
        # Group by levels
        levels = self.get_processing_order()
        
        for i, level in enumerate(levels):
            lines.append(f"Level {i + 1}: {', '.join(level)}")
        
        lines.append("\nRelationships:")
        lines.append("-" * 15)
        
        for rel in self.relationships:
            lines.append(f"{rel.from_entity}.{rel.from_property} -> {rel.to_entity}.{rel.to_property}")
        
        return "\n".join(lines)
    
    def get_graph_stats(self) -> Dict[str, int]:
        """Get statistics about the dependency graph"""
        return {
            'total_entities': len(self.graph.nodes()),
            'total_relationships': len(self.relationships),
            'independent_entities': len([n for n in self.graph.nodes() if self.is_independent(n)]),
            'processing_levels': len(self.get_processing_order()),
            'cycles_detected': len(list(nx.simple_cycles(self.graph)))
        }
