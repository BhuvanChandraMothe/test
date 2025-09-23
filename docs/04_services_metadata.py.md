# services/metadata.py - Metadata Service Documentation

## Overview
The `services/metadata.py` file implements the MetadataService class, which fetches and parses OData metadata (EDMX) from SAP services. It converts XML schema definitions into Python objects for use throughout the connector.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
import httpx
import structlog
from pyodata import Client
from pyodata.exceptions import PyODataException

from config.models import ODataConfig
```

**Library Concepts:**
- **xml.etree.ElementTree**: Python's built-in XML parsing library
- **httpx**: Modern async HTTP client library
- **structlog**: Structured logging for better observability
- **pyodata**: SAP-specific OData client library (imported but not used in current implementation)

### EntitySchema Class
```python
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
```

**Object-Oriented Design Patterns:**
- **Data encapsulation**: Entity schema data wrapped in class
- **Builder pattern**: Methods to add relationships incrementally
- **Dictionary storage**: Flexible storage for properties and relationships
- **Separation of concerns**: Schema structure separate from parsing logic

### MetadataService Class Structure
```python
class MetadataService:
    """Service to fetch and parse SAP OData metadata"""
    
    def __init__(self, odata_config: ODataConfig):
        self.odata_config = odata_config
        self.schemas: Dict[str, EntitySchema] = {}
        self._client: Optional[httpx.AsyncClient] = None
```

**Service Class Patterns:**
- **Dependency injection**: Configuration injected via constructor
- **State management**: Schemas stored as instance variable
- **Resource management**: HTTP client managed as instance variable
- **Optional typing**: Client initially None, created later

### Async Context Manager
```python
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.odata_config.timeout,
            verify=self.odata_config.verify_ssl
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
```

**Context Manager Concepts:**
- **`__aenter__`**: Called when entering `async with` block
- **`__aexit__`**: Called when exiting `async with` block (even on exceptions)
- **Resource management**: Ensures HTTP client is properly closed
- **Configuration integration**: Uses timeout and SSL settings from config

### Metadata Fetching
```python
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
```

**HTTP Request Patterns:**
- **Conditional authentication**: Only add auth if credentials provided
- **HTTP status checking**: `raise_for_status()` converts HTTP errors to exceptions
- **Exception handling**: Catch and re-raise with context
- **Structured logging**: Include relevant context in log messages

### EDMX XML Parsing
```python
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
```

**XML Parsing Concepts:**
- **Namespace handling**: OData V4 uses OASIS namespaces (different from V2)
- **XPath expressions**: `.//edm:EntitySet` finds all EntitySet elements
- **Attribute extraction**: `get('Name')` retrieves XML attributes
- **Namespace prefix removal**: `split('.')[-1]` removes namespace from type names
- **Two-phase parsing**: First map EntitySets to EntityTypes, then parse types

### EntityType Processing
```python
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
```

**Schema Extraction Patterns:**
- **Defensive programming**: Check if entity_name exists before processing
- **Key extraction**: Parse primary key definitions from Key element
- **Property parsing**: Extract all property definitions with metadata
- **Type conversion**: Convert string 'true'/'false' to boolean
- **Optional attributes**: Use `get()` with defaults for optional XML attributes

### EntitySet Name Mapping
```python
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
```

**Critical Design Decision:**
- **EntitySet vs EntityType**: EntityTypes define schema, EntitySets are queryable collections
- **Name mapping**: Use EntitySet names as keys for querying (e.g., "Categories" not "Category")
- **Fallback strategy**: Use EntityType name if no matching EntitySet found
- **Navigation properties**: Extract relationship information for dependency analysis

### Association Parsing
```python
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
```

**Relationship Analysis Concepts:**
- **Binary associations**: Relationships between two entities
- **Principal/Dependent**: Parent/child relationship roles
- **Referential constraints**: Foreign key definitions in XML
- **Role mapping**: Determine which entity is parent vs child
- **Property correlation**: Map foreign key properties to referenced properties

### Foreign Key Relationship Extraction
```python
def get_foreign_key_relationships(self) -> List[Dict[str, Any]]:
    """Extract foreign key relationships for dependency analysis"""
    relationships = []
    
    for entity_name, schema in self.schemas.items():
        for fk_prop, fk_info in schema.foreign_keys.items():
            relationships.append({
                'from_entity': entity_name,
                'to_entity': fk_info['referenced_entity'],
                'from_property': fk_prop,
                'to_property': fk_info['referenced_property'],
                'relationship_type': 'foreign_key'
            })
    
    return relationships
```

**Dependency Graph Building:**
- **Relationship extraction**: Convert schema relationships to graph edges
- **Standardized format**: Consistent relationship representation
- **Graph theory**: Prepare data for topological sorting
- **Processing order**: Enable dependency-aware processing

## Advanced XML Parsing Concepts

### Namespace Handling
```python
# OData V2 (older SAP systems)
namespaces_v2 = {
    'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx',
    'edm': 'http://schemas.microsoft.com/ado/2008/09/edm'
}

# OData V4 (modern systems)
namespaces_v4 = {
    'edmx': 'http://docs.oasis-open.org/odata/ns/edmx',
    'edm': 'http://docs.oasis-open.org/odata/ns/edm'
}
```

**Version Compatibility:**
- **Namespace evolution**: OData V4 uses different XML namespaces
- **Backward compatibility**: May need to detect and handle both versions
- **Standards compliance**: OASIS took over OData standardization

### Complex Type Handling
```python
# Example of parsing complex types (not in current implementation)
complex_types = root.findall('.//edm:ComplexType', namespaces)
for complex_type in complex_types:
    type_name = complex_type.get('Name')
    properties = {}
    
    for prop in complex_type.findall('edm:Property', namespaces):
        prop_name = prop.get('Name')
        prop_type = prop.get('Type')
        properties[prop_name] = {'type': prop_type}
```

### Function Import Parsing
```python
# Example of parsing function imports (not in current implementation)
function_imports = root.findall('.//edm:FunctionImport', namespaces)
for func_import in function_imports:
    func_name = func_import.get('Name')
    return_type = func_import.get('ReturnType')
    # Parse parameters, etc.
```

## Key Programming Concepts

### 1. **XML Processing with Namespaces**
```python
# Without namespaces (won't work with OData)
elements = root.findall('EntityType')  # Empty result

# With namespaces (correct)
elements = root.findall('.//edm:EntityType', namespaces)  # Finds elements
```

### 2. **Async Resource Management**
```python
async with MetadataService(config) as service:
    schemas = await service.fetch_metadata()
# HTTP client automatically closed here
```

### 3. **Schema-to-Object Mapping**
```python
# XML Schema
<EntityType Name="Product">
    <Key>
        <PropertyRef Name="ProductID"/>
    </Key>
    <Property Name="ProductID" Type="Edm.Int32" Nullable="false"/>
    <Property Name="ProductName" Type="Edm.String" MaxLength="40"/>
</EntityType>

# Python Object
schema = EntitySchema(
    name="Product",
    properties={
        "ProductID": {"type": "Edm.Int32", "nullable": False},
        "ProductName": {"type": "Edm.String", "nullable": True, "max_length": "40"}
    },
    keys=["ProductID"]
)
```

### 4. **Error Handling Strategy**
```python
try:
    response = await client.get(url)
    response.raise_for_status()  # HTTP errors
    root = ET.fromstring(response.text)  # XML parsing errors
except httpx.HTTPError as e:
    # Network/HTTP issues
    logger.error("HTTP error", error=str(e))
    raise
except ET.ParseError as e:
    # XML parsing issues
    logger.error("XML parsing error", error=str(e))
    raise
```

## Usage Examples

### Basic Metadata Fetching
```python
from services.metadata import MetadataService
from config.models import ODataConfig

config = ODataConfig(
    service_url="https://services.odata.org/V4/Northwind/Northwind.svc"
)

async with MetadataService(config) as service:
    schemas = await service.fetch_metadata()
    
    for name, schema in schemas.items():
        print(f"Entity: {name}")
        print(f"  Keys: {schema.keys}")
        print(f"  Properties: {len(schema.properties)}")
```

### Relationship Analysis
```python
async with MetadataService(config) as service:
    schemas = await service.fetch_metadata()
    relationships = service.get_foreign_key_relationships()
    
    for rel in relationships:
        print(f"{rel['from_entity']}.{rel['from_property']} -> "
              f"{rel['to_entity']}.{rel['to_property']}")
```

### Custom Schema Processing
```python
class ExtendedMetadataService(MetadataService):
    async def _parse_custom_annotations(self, root):
        """Parse SAP-specific annotations"""
        annotations = root.findall('.//edm:Annotation', self.namespaces)
        for annotation in annotations:
            term = annotation.get('Term')
            if term and term.startswith('SAP.'):
                # Process SAP-specific metadata
                pass
```

This file demonstrates enterprise-grade XML processing, async resource management, and schema modeling for OData services.
