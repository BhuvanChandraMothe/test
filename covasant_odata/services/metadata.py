import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
import httpx
import structlog
from pyodata import Client
from pyodata.exceptions import PyODataException



from ..config.models import ODataConfig

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
        self.odata_version: Optional[str] = None  # Track OData version (V2 or V4)
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.odata_config.timeout,
            verify=self.odata_config.verify_ssl
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def test_connection(self) -> bool:
        """Test connection to OData service by fetching metadata"""
        logger.info("Testing connection to OData service", url=self.odata_config.metadata_url)
        
        try:
            # Prepare authentication
            auth = None
            if self.odata_config.username and self.odata_config.password:
                auth = (self.odata_config.username, self.odata_config.password)
            
            # Test connection with metadata endpoint
            response = await self._client.get(
                self.odata_config.metadata_url,
                auth=auth,
                timeout=10.0  # Short timeout for connection test
            )
            
            if response.status_code == 200:
                logger.info(" Connection test successful", 
                           status_code=response.status_code,
                           content_type=response.headers.get('content-type', 'unknown'))
                return True
            elif response.status_code == 401:
                logger.error("FAILED: Connection test failed: Authentication required or invalid credentials",
                           status_code=response.status_code)
                return False
            elif response.status_code == 403:
                logger.error("FAILED: Connection test failed: Access forbidden",
                           status_code=response.status_code)
                return False
            elif response.status_code == 404:
                logger.error("FAILED: Connection test failed: Service not found",
                           status_code=response.status_code)
                return False
            else:
                logger.error("FAILED: Connection test failed: Unexpected response",
                           status_code=response.status_code)
                return False
                
        except httpx.TimeoutException:
            logger.error("FAILED: Connection test failed: Request timeout")
            return False
        except httpx.ConnectError:
            logger.error("FAILED: Connection test failed: Cannot connect to server")
            return False
        except httpx.HTTPError as e:
            logger.error("FAILED: Connection test failed: HTTP error", error=str(e))
            return False
        except Exception as e:
            logger.error("FAILED: Connection test failed: Unexpected error", error=str(e))
            return False

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
        
        # Try different namespace versions (V2 and V4)
        namespaces_v4 = {
            'edmx': 'http://docs.oasis-open.org/odata/ns/edmx',
            'edm': 'http://docs.oasis-open.org/odata/ns/edm'
        }
        namespaces_v2 = {
            'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx',
            'edm': 'http://schemas.microsoft.com/ado/2008/09/edm'
        }
        
        # Detect which namespace version to use
        namespaces = namespaces_v4
        if root.findall('.//edm:EntitySet', namespaces_v2):
            namespaces = namespaces_v2
            self.odata_version = 'V2'
            logger.info("Using OData V2 namespaces for metadata parsing")
        else:
            self.odata_version = 'V4'
            logger.info("Using OData V4 namespaces for metadata parsing")
        
        # First, build a mapping of EntitySet names to EntityType names
        entity_set_mapping = {}
        entity_type_to_set_mapping = {}
        entity_sets = root.findall('.//edm:EntitySet', namespaces)
        for entity_set in entity_sets:
            set_name = entity_set.get('Name')
            type_name = entity_set.get('EntityType')
            if set_name and type_name:
                # Remove namespace prefix from type name
                type_name = type_name.split('.')[-1]
                entity_set_mapping[type_name] = set_name # Store mapping from EntityType to EntitySet
                entity_type_to_set_mapping[set_name] = type_name
        
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
            
            # Extract navigation properties (OData V4 style)
            for nav_prop in entity_type.findall('edm:NavigationProperty', namespaces):
                nav_name = nav_prop.get('Name')
                nav_type = nav_prop.get('Type')
                partner = nav_prop.get('Partner')
                
                if nav_name and nav_type:
                    # Extract target entity from type (remove Collection() wrapper and namespace)
                    target_type = nav_type
                    if target_type.startswith('Collection('):
                        target_type = target_type[11:-1]  # Remove Collection( and )
                    target_entity = target_type.split('.')[-1]  # Remove namespace
                    
                    # Map to EntitySet name if available
                    target_set = entity_set_mapping.get(target_entity, target_entity)
                    
                    schema.add_navigation_property(nav_name, target_set, nav_type)
            
            # Store schema using EntitySet name if available, otherwise EntityType name
            schema_key = entity_set_mapping.get(entity_name, entity_name) # Use the mapped EntitySet name if it exists
            self.schemas[schema_key] = schema
        
        # Parse foreign key relationships (OData V4 style)
        await self._parse_v4_relationships(root, namespaces, entity_set_mapping)
        
        # Also try legacy associations for backward compatibility
        await self._parse_associations(root, namespaces)
    
    async def _parse_v4_relationships(self, root: ET.Element, namespaces: Dict[str, str], entity_set_mapping: Dict[str, str]):
        """Parse OData V4 style relationships using NavigationProperty and inferred foreign keys"""
        #logger.info("Parsing OData V4 relationships...")
        
        # Find all entity types to process their navigation properties
        entity_types = root.findall('.//edm:EntityType', namespaces)
        
        for entity_type in entity_types:
            entity_name = entity_type.get('Name')
            if not entity_name:
                continue
                
            entity_set_name = entity_set_mapping.get(entity_name, entity_name)
            
            # Get all properties for this entity
            properties = {}
            for prop in entity_type.findall('edm:Property', namespaces):
                prop_name = prop.get('Name')
                prop_type = prop.get('Type')
                if prop_name:
                    properties[prop_name] = prop_type
            
            # Process navigation properties
            for nav_prop in entity_type.findall('edm:NavigationProperty', namespaces):
                nav_name = nav_prop.get('Name')
                nav_type = nav_prop.get('Type')
                
                if not nav_name or not nav_type:
                    continue
                
                # Extract target entity from type
                target_type = nav_type
                is_collection = target_type.startswith('Collection(')
                if is_collection:
                    target_type = target_type[11:-1]  # Remove Collection( and )
                target_entity = target_type.split('.')[-1]  # Remove namespace
                target_set_name = entity_set_mapping.get(target_entity, target_entity)
                
                # Look for explicit referential constraint first
                ref_constraint = nav_prop.find('edm:ReferentialConstraint', namespaces)
                if ref_constraint is not None:
                    property_elem = ref_constraint.get('Property')
                    referenced_property_elem = ref_constraint.get('ReferencedProperty')
                    
                    if property_elem and referenced_property_elem:
                        # Add foreign key relationship
                        if entity_set_name in self.schemas:
                            self.schemas[entity_set_name].add_foreign_key(
                                property_elem, 
                                target_set_name, 
                                referenced_property_elem
                            )
                            logger.debug(f"Added FK (explicit): {entity_set_name}.{property_elem} -> {target_set_name}.{referenced_property_elem}")
                else:
                    # No explicit referential constraint, try to infer from naming conventions
                    # For non-collection navigation properties (many-to-one relationships)
                    if not is_collection:
                        # Look for a property that matches the target entity + "ID"
                        potential_fk_names = [
                            f"{target_entity}ID",  # e.g., CategoryID
                            f"{nav_name}ID",       # e.g., CategoryID if nav_name is Category
                            f"{target_entity}Id",  # Alternative casing
                            f"{nav_name}Id"        # Alternative casing
                        ]
                        
                        for fk_name in potential_fk_names:
                            if fk_name in properties:
                                # Found a potential foreign key property
                                if entity_set_name in self.schemas:
                                    # Assume it references the primary key of the target entity
                                    target_pk = f"{target_entity}ID"  # Common convention
                                    self.schemas[entity_set_name].add_foreign_key(
                                        fk_name, 
                                        target_set_name, 
                                        target_pk
                                    )
                                    logger.debug(f"Added FK (inferred): {entity_set_name}.{fk_name} -> {target_set_name}.{target_pk}")
                                break
        
        #logger.info(f"Completed V4 relationship parsing")
    
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
                        
                        # Map entity type names to entity set names
                        dependent_set_name = None
                        principal_set_name = None
                        
                        # Find the correct entity set names
                        for set_name, schema in self.schemas.items():
                            if schema.name == dependent_entity:
                                dependent_set_name = set_name
                            if schema.name == principal_entity:
                                principal_set_name = set_name
                        
                        # Add foreign key relationships if we found the entities
                        if dependent_set_name and principal_set_name and dependent_set_name in self.schemas:
                            for dep_prop, prin_prop in zip(dependent_props, principal_props):
                                self.schemas[dependent_set_name].add_foreign_key(
                                    dep_prop, principal_set_name, prin_prop
                                )
                                logger.debug(f"Added FK (legacy): {dependent_set_name}.{dep_prop} -> {principal_set_name}.{prin_prop}")

    
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
    
    async def save_entity_relationship_file(self, output_directory: str) -> str:
        """Save metadata as an Entity Relationship file in JSON format"""
        import json
        from pathlib import Path
        from datetime import datetime
        
        logger.info("Saving Entity Relationship file", output_dir=output_directory)
        
        # Create output directory if it doesn't exist
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create ER data structure
        er_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "service_url": self.odata_config.service_url,
                "total_entities": len(self.schemas)
            },
            "entities": {},
            "relationships": self.get_foreign_key_relationships(),
            "summary": {
                "entity_count": len(self.schemas),
                "relationship_count": sum(len(rels) for rels in self.get_foreign_key_relationships().values())
            }
        }
        
        # Add detailed entity information
        for entity_name, schema in self.schemas.items():
            er_data["entities"][entity_name] = {
                "name": schema.name,
                "properties": schema.properties,
                "keys": schema.keys,
                "navigation_properties": schema.navigation_properties,
                "foreign_keys": schema.foreign_keys,
                "property_count": len(schema.properties),
                "key_count": len(schema.keys),
                "navigation_count": len(schema.navigation_properties)
            }
        
        # Save to file
        er_file_path = output_path / "entity_relationships.json"
        
        try:
            with open(er_file_path, 'w', encoding='utf-8') as f:
                json.dump(er_data, f, indent=2, ensure_ascii=False)
            
            logger.info(" Entity Relationship file saved successfully", 
                       file_path=str(er_file_path),
                       entities=len(self.schemas),
                       file_size_kb=round(er_file_path.stat().st_size / 1024, 2))
            
            return str(er_file_path)
            
        except Exception as e:
            logger.error("FAILED: Failed to save Entity Relationship file", 
                        error=str(e), 
                        file_path=str(er_file_path))
            raise