"""Metadata service for SAP OData connector"""

import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
import httpx
import structlog
from pyodata import Client
from pyodata.exceptions import PyODataException



from config.models import ODataConfig

logger = structlog.get_logger(__name__)


class EntitySchema:
    """Represents an OData entity schema"""
    
    def __init__(self, name: str, properties: Dict[str, Any], keys: List[str]):
        self.name = name
        self.properties = properties
        self.keys = keys
        self.navigation_properties = {}
        self.foreign_keys = {}
    
    def add_navigation_property(self, name: str, target_entity: str, relationship_type: str):
        """Add a navigation property (foreign key relationship)"""
        self.navigation_properties[name] = {
            'target_entity': target_entity,
            'relationship_type': relationship_type
        }
    
    def add_foreign_key(self, property_name: str, referenced_entity: str, referenced_property: str):
        """Add foreign key information"""
        self.foreign_keys[property_name] = {
            'referenced_entity': referenced_entity,
            'referenced_property': referenced_property
        }


class MetadataService:
    """Service to fetch and parse SAP OData metadata"""
    
    def __init__(self, odata_config: ODataConfig):
        self.odata_config = odata_config
        self.schemas: Dict[str, EntitySchema] = {}
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.odata_config.timeout,
            verify=self.odata_config.verify_ssl
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def fetch_metadata(self) -> Dict[str, EntitySchema]:
        """Fetch and parse metadata from SAP OData service"""
        logger.info("Fetching metadata from OData service", url=self.odata_config.metadata_url)
        
        try:
            # Fetch EDMX metadata
            auth = None
            if self.odata_config.username and self.odata_config.password:
                auth = (self.odata_config.username, self.odata_config.password)
            
            response = await self._client.get(
                self.odata_config.metadata_url,
                auth=auth
            )
            response.raise_for_status()
            
            # Parse EDMX XML
            edmx_content = response.text
            await self._parse_edmx(edmx_content)
            
            logger.info("Successfully parsed metadata", entity_count=len(self.schemas))
            return self.schemas
            
        except httpx.HTTPError as e:
            logger.error("Failed to fetch metadata", error=str(e))
            raise
        except ET.ParseError as e:
            logger.error("Failed to parse EDMX metadata", error=str(e))
            raise
    
    async def _parse_edmx(self, edmx_content: str):
        """Parse EDMX XML content and extract entity schemas"""
        root = ET.fromstring(edmx_content)
        
        # Define namespaces (OData V4 uses newer OASIS namespaces)
        namespaces = {
            'edmx': 'http://docs.oasis-open.org/odata/ns/edmx',
            'edm': 'http://docs.oasis-open.org/odata/ns/edm'
        }
        
        # First, build a mapping of EntitySet names to EntityType names
        entity_set_mapping = {}
        entity_sets = root.findall('.//edm:EntitySet', namespaces)
        for entity_set in entity_sets:
            set_name = entity_set.get('Name')
            type_name = entity_set.get('EntityType')
            if set_name and type_name:
                # Remove namespace prefix from type name
                type_name = type_name.split('.')[-1]
                entity_set_mapping[set_name] = type_name
        
        # Find all entity types
        entity_types = root.findall('.//edm:EntityType', namespaces)
        
        for entity_type in entity_types:
            entity_name = entity_type.get('Name')
            if not entity_name:
                continue
            
            # Extract properties
            properties = {}
            keys = []
            
            # Get key properties
            key_element = entity_type.find('edm:Key', namespaces)
            if key_element is not None:
                for prop_ref in key_element.findall('edm:PropertyRef', namespaces):
                    keys.append(prop_ref.get('Name'))
            
            # Get all properties
            for prop in entity_type.findall('edm:Property', namespaces):
                prop_name = prop.get('Name')
                prop_type = prop.get('Type')
                nullable = prop.get('Nullable', 'true').lower() == 'true'
                max_length = prop.get('MaxLength')
                
                properties[prop_name] = {
                    'type': prop_type,
                    'nullable': nullable,
                    'max_length': max_length
                }
            
            # Create entity schema
            schema = EntitySchema(entity_name, properties, keys)
            
            # Extract navigation properties
            for nav_prop in entity_type.findall('edm:NavigationProperty', namespaces):
                nav_name = nav_prop.get('Name')
                relationship = nav_prop.get('Relationship')
                to_role = nav_prop.get('ToRole')
                
                if nav_name and relationship:
                    schema.add_navigation_property(nav_name, to_role or 'Unknown', relationship)
            
            # Store schema using EntitySet name if available, otherwise EntityType name
            entity_set_name = None
            for set_name, type_name in entity_set_mapping.items():
                if type_name == entity_name:
                    entity_set_name = set_name
                    break
            
            # Use EntitySet name for querying, but keep EntityType info
            schema_key = entity_set_name if entity_set_name else entity_name
            self.schemas[schema_key] = schema
        
        # Parse associations for foreign key relationships
        await self._parse_associations(root, namespaces)
    
    async def _parse_associations(self, root: ET.Element, namespaces: Dict[str, str]):
        """Parse association elements to identify foreign key relationships"""
        associations = root.findall('.//edm:Association', namespaces)
        
        for association in associations:
            association_name = association.get('Name')
            ends = association.findall('edm:End', namespaces)
            
            if len(ends) == 2:
                # This is a binary association
                end1, end2 = ends
                entity1 = end1.get('Type', '').split('.')[-1]  # Remove namespace
                entity2 = end2.get('Type', '').split('.')[-1]
                
                # Look for referential constraints
                ref_constraint = association.find('edm:ReferentialConstraint', namespaces)
                if ref_constraint is not None:
                    principal = ref_constraint.find('edm:Principal', namespaces)
                    dependent = ref_constraint.find('edm:Dependent', namespaces)
                    
                    if principal is not None and dependent is not None:
                        principal_role = principal.get('Role')
                        dependent_role = dependent.get('Role')
                        
                        # Get property references
                        principal_props = [p.get('Name') for p in principal.findall('edm:PropertyRef', namespaces)]
                        dependent_props = [p.get('Name') for p in dependent.findall('edm:PropertyRef', namespaces)]
                        
                        # Add foreign key relationships
                        if dependent_role == end1.get('Role'):
                            dependent_entity = entity1
                            principal_entity = entity2
                        else:
                            dependent_entity = entity2
                            principal_entity = entity1
                        
                        if dependent_entity in self.schemas:
                            for dep_prop, prin_prop in zip(dependent_props, principal_props):
                                self.schemas[dependent_entity].add_foreign_key(
                                    dep_prop, principal_entity, prin_prop
                                )
    
    def get_entity_sets(self) -> List[str]:
        """Get list of all entity set names"""
        return list(self.schemas.keys())
    
    def get_entity_schema(self, entity_name: str) -> Optional[EntitySchema]:
        """Get schema for a specific entity"""
        return self.schemas.get(entity_name)
    
    def get_foreign_key_relationships(self) -> Dict[str, List[Dict[str, str]]]:
        """Get all foreign key relationships for dependency graph building"""
        relationships = {}
        
        for entity_name, schema in self.schemas.items():
            entity_relationships = []
            
            for fk_prop, fk_info in schema.foreign_keys.items():
                entity_relationships.append({
                    'from_entity': entity_name,
                    'to_entity': fk_info['referenced_entity'],
                    'from_property': fk_prop,
                    'to_property': fk_info['referenced_property']
                })
            
            if entity_relationships:
                relationships[entity_name] = entity_relationships
        
        return relationships
