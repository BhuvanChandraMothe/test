# transformation/data_transformer.py - Data Transformation Documentation

## Overview
The `transformation/data_transformer.py` file implements the DataTransformer class, which handles data cleaning, validation, and transformation of OData records. It provides configurable transformation pipelines for converting raw OData responses into structured, validated data.

## File Structure Analysis

### Imports and Dependencies
```python
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timezone
import re
import structlog
from decimal import Decimal, InvalidOperation

from services.metadata import EntitySchema
```

**Library Concepts:**
- **datetime**: Date/time parsing and timezone handling
- **decimal**: Precise decimal arithmetic for financial data
- **re**: Regular expressions for data validation and cleaning
- **typing**: Advanced type hints for transformation functions
- **structlog**: Structured logging for transformation tracking

### TransformationRule Data Class
```python
@dataclass
class TransformationRule:
    """Defines a single transformation rule"""
    
    field_name: str
    rule_type: str  # "clean", "validate", "convert", "derive"
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Callable[[Any], bool]] = None
    error_action: str = "skip"  # "skip", "default", "error"
    default_value: Any = None
    
    def __post_init__(self):
        """Validate rule configuration"""
        valid_types = ["clean", "validate", "convert", "derive"]
        if self.rule_type not in valid_types:
            raise ValueError(f"Invalid rule_type: {self.rule_type}")
        
        valid_actions = ["skip", "default", "error"]
        if self.error_action not in valid_actions:
            raise ValueError(f"Invalid error_action: {self.error_action}")
```

**Rule-Based Transformation Design:**
- **Rule types**: Different categories of transformations
- **Conditional application**: Apply rules based on conditions
- **Error handling**: Configurable error response strategies
- **Parameter flexibility**: Rules can have custom parameters
- **Validation**: Ensure rule configuration is valid

### DataTransformer Class Structure
```python
class DataTransformer:
    """Handles data transformation and validation for OData records"""
    
    def __init__(self, schemas: Dict[str, EntitySchema]):
        self.schemas = schemas
        self.transformation_rules: Dict[str, List[TransformationRule]] = {}
        self.logger = structlog.get_logger(__name__)
        
        # Statistics tracking
        self.stats = {
            'records_processed': 0,
            'records_transformed': 0,
            'validation_errors': 0,
            'transformation_errors': 0
        }
        
        # Built-in transformations
        self._register_builtin_transformations()
    
    def _register_builtin_transformations(self) -> None:
        """Register common transformation functions"""
        self.builtin_transformations = {
            'trim_whitespace': self._trim_whitespace,
            'normalize_case': self._normalize_case,
            'parse_datetime': self._parse_datetime,
            'parse_decimal': self._parse_decimal,
            'validate_email': self._validate_email,
            'clean_phone': self._clean_phone_number,
            'extract_numeric': self._extract_numeric,
            'standardize_boolean': self._standardize_boolean
        }
```

**Transformer Architecture:**
- **Schema-driven**: Use entity schemas for validation
- **Rule-based**: Configurable transformation rules per entity
- **Statistics tracking**: Monitor transformation performance
- **Built-in functions**: Common transformations ready to use
- **Extensible**: Easy to add custom transformation functions

### Record Transformation Pipeline
```python
async def transform_records(
    self, 
    entity_name: str, 
    records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Transform a list of records for an entity"""
    
    if not records:
        return []
    
    self.logger.info("Starting record transformation", 
                    entity=entity_name,
                    record_count=len(records))
    
    schema = self.schemas.get(entity_name)
    if not schema:
        self.logger.warning("No schema found for entity", entity=entity_name)
        return records  # Return unchanged if no schema
    
    transformed_records = []
    
    for i, record in enumerate(records):
        try:
            transformed_record = await self._transform_single_record(
                entity_name, record, schema
            )
            
            if transformed_record is not None:
                transformed_records.append(transformed_record)
                self.stats['records_transformed'] += 1
            
            self.stats['records_processed'] += 1
            
        except Exception as e:
            self.stats['transformation_errors'] += 1
            self.logger.error("Record transformation failed", 
                            entity=entity_name,
                            record_index=i,
                            error=str(e))
            # Continue with other records
    
    self.logger.info("Record transformation completed", 
                    entity=entity_name,
                    input_count=len(records),
                    output_count=len(transformed_records))
    
    return transformed_records
```

**Pipeline Processing:**
- **Batch processing**: Transform multiple records efficiently
- **Error isolation**: Individual record failures don't stop processing
- **Schema validation**: Use entity schemas for validation
- **Statistics tracking**: Monitor success/failure rates
- **Async processing**: Non-blocking transformation operations

### Single Record Transformation
```python
async def _transform_single_record(
    self, 
    entity_name: str, 
    record: Dict[str, Any], 
    schema: EntitySchema
) -> Optional[Dict[str, Any]]:
    """Transform a single record"""
    
    transformed_record = record.copy()  # Don't modify original
    
    # Apply entity-specific transformation rules
    rules = self.transformation_rules.get(entity_name, [])
    
    for rule in rules:
        try:
            # Check if rule condition is met
            if rule.condition and not rule.condition(transformed_record):
                continue
            
            # Apply transformation based on rule type
            if rule.rule_type == "clean":
                transformed_record = await self._apply_cleaning_rule(
                    transformed_record, rule
                )
            elif rule.rule_type == "validate":
                is_valid = await self._apply_validation_rule(
                    transformed_record, rule
                )
                if not is_valid:
                    return self._handle_validation_error(rule, transformed_record)
            elif rule.rule_type == "convert":
                transformed_record = await self._apply_conversion_rule(
                    transformed_record, rule
                )
            elif rule.rule_type == "derive":
                transformed_record = await self._apply_derivation_rule(
                    transformed_record, rule
                )
        
        except Exception as e:
            self.logger.error("Rule application failed", 
                            entity=entity_name,
                            rule=rule.field_name,
                            error=str(e))
            
            if rule.error_action == "error":
                raise
            elif rule.error_action == "default" and rule.default_value is not None:
                transformed_record[rule.field_name] = rule.default_value
            # "skip" action: continue without modification
    
    # Apply schema-based validation
    validated_record = await self._validate_against_schema(
        transformed_record, schema
    )
    
    return validated_record
```

**Single Record Processing:**
- **Immutable processing**: Don't modify original records
- **Rule application**: Apply transformation rules in sequence
- **Conditional rules**: Skip rules that don't meet conditions
- **Error handling**: Configurable error response per rule
- **Schema validation**: Final validation against entity schema

### Data Cleaning Operations
```python
async def _apply_cleaning_rule(
    self, 
    record: Dict[str, Any], 
    rule: TransformationRule
) -> Dict[str, Any]:
    """Apply data cleaning transformations"""
    
    field_name = rule.field_name
    if field_name not in record:
        return record
    
    value = record[field_name]
    transformation = rule.parameters.get('transformation')
    
    if transformation in self.builtin_transformations:
        # Apply built-in transformation
        cleaned_value = await self.builtin_transformations[transformation](
            value, rule.parameters
        )
        record[field_name] = cleaned_value
    
    return record

async def _trim_whitespace(self, value: Any, params: Dict[str, Any]) -> Any:
    """Remove leading/trailing whitespace"""
    if isinstance(value, str):
        return value.strip()
    return value

async def _normalize_case(self, value: Any, params: Dict[str, Any]) -> Any:
    """Normalize string case"""
    if not isinstance(value, str):
        return value
    
    case_type = params.get('case', 'lower')
    if case_type == 'lower':
        return value.lower()
    elif case_type == 'upper':
        return value.upper()
    elif case_type == 'title':
        return value.title()
    elif case_type == 'capitalize':
        return value.capitalize()
    
    return value

async def _clean_phone_number(self, value: Any, params: Dict[str, Any]) -> Any:
    """Clean and standardize phone numbers"""
    if not isinstance(value, str):
        return value
    
    # Remove all non-digit characters
    digits_only = re.sub(r'[^\d]', '', value)
    
    # Format based on length
    if len(digits_only) == 10:
        return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
    
    return value  # Return original if can't format
```

**Data Cleaning Features:**
- **Built-in cleaners**: Common cleaning operations ready to use
- **Whitespace handling**: Remove unwanted spaces
- **Case normalization**: Standardize text case
- **Phone formatting**: Standardize phone number formats
- **Regex processing**: Pattern-based cleaning

### Data Type Conversion
```python
async def _apply_conversion_rule(
    self, 
    record: Dict[str, Any], 
    rule: TransformationRule
) -> Dict[str, Any]:
    """Apply data type conversions"""
    
    field_name = rule.field_name
    if field_name not in record:
        return record
    
    value = record[field_name]
    target_type = rule.parameters.get('target_type')
    
    try:
        if target_type == 'datetime':
            converted_value = await self._parse_datetime(value, rule.parameters)
        elif target_type == 'decimal':
            converted_value = await self._parse_decimal(value, rule.parameters)
        elif target_type == 'boolean':
            converted_value = await self._standardize_boolean(value, rule.parameters)
        elif target_type == 'integer':
            converted_value = int(float(str(value))) if value is not None else None
        elif target_type == 'float':
            converted_value = float(str(value)) if value is not None else None
        elif target_type == 'string':
            converted_value = str(value) if value is not None else None
        else:
            self.logger.warning("Unknown conversion type", target_type=target_type)
            return record
        
        record[field_name] = converted_value
        
    except (ValueError, TypeError, InvalidOperation) as e:
        self.logger.warning("Type conversion failed", 
                          field=field_name,
                          value=value,
                          target_type=target_type,
                          error=str(e))
        
        if rule.error_action == "default":
            record[field_name] = rule.default_value
        elif rule.error_action == "error":
            raise
    
    return record

async def _parse_datetime(self, value: Any, params: Dict[str, Any]) -> Optional[datetime]:
    """Parse various datetime formats"""
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if not isinstance(value, str):
        value = str(value)
    
    # Try common datetime formats
    formats = params.get('formats', [
        '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO format with microseconds
        '%Y-%m-%dT%H:%M:%SZ',     # ISO format
        '%Y-%m-%d %H:%M:%S',      # Standard format
        '%Y-%m-%d',               # Date only
        '%m/%d/%Y',               # US format
        '%d/%m/%Y'                # European format
    ])
    
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            # Add timezone if not present
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    # If all formats fail, try to parse ISO format
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(f"Unable to parse datetime: {value}")

async def _parse_decimal(self, value: Any, params: Dict[str, Any]) -> Optional[Decimal]:
    """Parse decimal values with precision"""
    if value is None:
        return None
    
    if isinstance(value, Decimal):
        return value
    
    # Convert to string and clean
    str_value = str(value).strip()
    
    # Remove currency symbols and commas
    cleaned_value = re.sub(r'[$,€£¥]', '', str_value)
    
    try:
        return Decimal(cleaned_value)
    except InvalidOperation:
        raise ValueError(f"Unable to parse decimal: {value}")
```

**Type Conversion Features:**
- **Multiple formats**: Support various input formats
- **Error handling**: Graceful handling of conversion failures
- **Precision preservation**: Use Decimal for financial data
- **Timezone handling**: Proper datetime timezone management
- **Currency cleaning**: Remove currency symbols before conversion

### Data Validation
```python
async def _apply_validation_rule(
    self, 
    record: Dict[str, Any], 
    rule: TransformationRule
) -> bool:
    """Apply validation rules"""
    
    field_name = rule.field_name
    if field_name not in record:
        return rule.parameters.get('allow_missing', False)
    
    value = record[field_name]
    validation_type = rule.parameters.get('validation_type')
    
    try:
        if validation_type == 'required':
            return value is not None and str(value).strip() != ''
        
        elif validation_type == 'email':
            return await self._validate_email(value, rule.parameters)
        
        elif validation_type == 'range':
            min_val = rule.parameters.get('min')
            max_val = rule.parameters.get('max')
            num_value = float(value)
            return (min_val is None or num_value >= min_val) and \
                   (max_val is None or num_value <= max_val)
        
        elif validation_type == 'length':
            min_len = rule.parameters.get('min_length', 0)
            max_len = rule.parameters.get('max_length', float('inf'))
            str_value = str(value)
            return min_len <= len(str_value) <= max_len
        
        elif validation_type == 'pattern':
            pattern = rule.parameters.get('pattern')
            return bool(re.match(pattern, str(value)))
        
        elif validation_type == 'custom':
            validator_func = rule.parameters.get('validator')
            if callable(validator_func):
                return validator_func(value)
        
        return True
        
    except Exception as e:
        self.logger.error("Validation error", 
                         field=field_name,
                         validation_type=validation_type,
                         error=str(e))
        return False

async def _validate_email(self, value: Any, params: Dict[str, Any]) -> bool:
    """Validate email address format"""
    if not isinstance(value, str):
        return False
    
    # Simple email regex (can be enhanced)
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, value))
```

**Validation Features:**
- **Multiple validation types**: Required, email, range, length, pattern
- **Custom validators**: Support for custom validation functions
- **Missing field handling**: Configurable behavior for missing fields
- **Error resilience**: Continue validation even if some rules fail
- **Regex patterns**: Pattern-based validation

### Data Derivation
```python
async def _apply_derivation_rule(
    self, 
    record: Dict[str, Any], 
    rule: TransformationRule
) -> Dict[str, Any]:
    """Apply data derivation rules to create new fields"""
    
    derivation_type = rule.parameters.get('derivation_type')
    target_field = rule.parameters.get('target_field', rule.field_name)
    
    try:
        if derivation_type == 'concatenate':
            # Concatenate multiple fields
            source_fields = rule.parameters.get('source_fields', [])
            separator = rule.parameters.get('separator', ' ')
            
            values = []
            for field in source_fields:
                if field in record and record[field] is not None:
                    values.append(str(record[field]))
            
            record[target_field] = separator.join(values)
        
        elif derivation_type == 'calculate':
            # Perform calculations
            expression = rule.parameters.get('expression')
            if expression:
                # Simple expression evaluation (can be enhanced with safe eval)
                result = self._evaluate_expression(expression, record)
                record[target_field] = result
        
        elif derivation_type == 'lookup':
            # Lookup values from mapping
            source_field = rule.parameters.get('source_field')
            mapping = rule.parameters.get('mapping', {})
            default = rule.parameters.get('default')
            
            if source_field in record:
                source_value = record[source_field]
                record[target_field] = mapping.get(source_value, default)
        
        elif derivation_type == 'extract':
            # Extract part of a field value
            source_field = rule.parameters.get('source_field')
            pattern = rule.parameters.get('pattern')
            group = rule.parameters.get('group', 0)
            
            if source_field in record and pattern:
                match = re.search(pattern, str(record[source_field]))
                if match:
                    record[target_field] = match.group(group)
    
    except Exception as e:
        self.logger.error("Derivation rule failed", 
                         rule_type=derivation_type,
                         error=str(e))
        
        if rule.error_action == "default":
            record[target_field] = rule.default_value
        elif rule.error_action == "error":
            raise
    
    return record

def _evaluate_expression(self, expression: str, record: Dict[str, Any]) -> Any:
    """Safely evaluate mathematical expressions"""
    # This is a simplified implementation
    # In production, use a safe expression evaluator
    
    # Replace field references with values
    for field, value in record.items():
        if isinstance(value, (int, float)):
            expression = expression.replace(f'{{{field}}}', str(value))
    
    try:
        # Very basic evaluation - enhance with ast.literal_eval or similar
        return eval(expression)
    except:
        return None
```

**Data Derivation Features:**
- **Field concatenation**: Combine multiple fields
- **Calculations**: Perform mathematical operations
- **Lookup tables**: Map values using dictionaries
- **Pattern extraction**: Extract data using regex patterns
- **Expression evaluation**: Calculate derived values

### Schema-Based Validation
```python
async def _validate_against_schema(
    self, 
    record: Dict[str, Any], 
    schema: EntitySchema
) -> Optional[Dict[str, Any]]:
    """Validate record against entity schema"""
    
    validated_record = record.copy()
    
    # Check required fields (primary keys)
    for key_field in schema.keys:
        if key_field not in validated_record or validated_record[key_field] is None:
            self.logger.error("Missing required key field", 
                            field=key_field,
                            record_keys=list(validated_record.keys()))
            self.stats['validation_errors'] += 1
            return None
    
    # Validate field types based on schema
    for field_name, field_info in schema.properties.items():
        if field_name not in validated_record:
            continue
        
        value = validated_record[field_name]
        if value is None:
            # Check if field is nullable
            if not field_info.get('nullable', True):
                self.logger.warning("Non-nullable field is null", 
                                  field=field_name)
                self.stats['validation_errors'] += 1
            continue
        
        # Validate field type
        odata_type = field_info.get('type', '')
        if not await self._validate_odata_type(value, odata_type):
            self.logger.warning("Type validation failed", 
                              field=field_name,
                              value=value,
                              expected_type=odata_type)
            self.stats['validation_errors'] += 1
    
    return validated_record

async def _validate_odata_type(self, value: Any, odata_type: str) -> bool:
    """Validate value against OData type"""
    
    type_mapping = {
        'Edm.String': str,
        'Edm.Int32': int,
        'Edm.Int64': int,
        'Edm.Double': (int, float),
        'Edm.Decimal': (int, float, Decimal),
        'Edm.Boolean': bool,
        'Edm.DateTime': datetime,
        'Edm.DateTimeOffset': datetime
    }
    
    expected_types = type_mapping.get(odata_type)
    if expected_types is None:
        return True  # Unknown type, assume valid
    
    if not isinstance(expected_types, tuple):
        expected_types = (expected_types,)
    
    return isinstance(value, expected_types)
```

**Schema Validation Features:**
- **Required field checking**: Ensure primary keys are present
- **Type validation**: Validate against OData type definitions
- **Nullable field handling**: Check nullable constraints
- **Type mapping**: Map OData types to Python types
- **Error tracking**: Count validation errors for reporting

## Advanced Transformation Concepts

### Transformation Rule Builder
```python
class TransformationRuleBuilder:
    """Fluent interface for building transformation rules"""
    
    def __init__(self, field_name: str):
        self.rule = TransformationRule(field_name=field_name, rule_type="clean")
    
    def clean_with(self, transformation: str, **params) -> 'TransformationRuleBuilder':
        self.rule.rule_type = "clean"
        self.rule.parameters = {'transformation': transformation, **params}
        return self
    
    def validate_as(self, validation_type: str, **params) -> 'TransformationRuleBuilder':
        self.rule.rule_type = "validate"
        self.rule.parameters = {'validation_type': validation_type, **params}
        return self
    
    def convert_to(self, target_type: str, **params) -> 'TransformationRuleBuilder':
        self.rule.rule_type = "convert"
        self.rule.parameters = {'target_type': target_type, **params}
        return self
    
    def when(self, condition: Callable[[Dict[str, Any]], bool]) -> 'TransformationRuleBuilder':
        self.rule.condition = condition
        return self
    
    def on_error(self, action: str, default_value: Any = None) -> 'TransformationRuleBuilder':
        self.rule.error_action = action
        self.rule.default_value = default_value
        return self
    
    def build(self) -> TransformationRule:
        return self.rule

# Usage example:
rule = (TransformationRuleBuilder("email")
        .clean_with("trim_whitespace")
        .validate_as("email")
        .on_error("skip")
        .build())
```

### Custom Transformation Functions
```python
class CustomTransformations:
    """Custom transformation functions for specific business logic"""
    
    @staticmethod
    async def standardize_country_code(value: Any, params: Dict[str, Any]) -> str:
        """Standardize country codes to ISO format"""
        country_mapping = {
            'US': 'USA', 'United States': 'USA',
            'UK': 'GBR', 'United Kingdom': 'GBR',
            'DE': 'DEU', 'Germany': 'DEU'
        }
        
        if isinstance(value, str):
            return country_mapping.get(value.strip(), value)
        return value
    
    @staticmethod
    async def calculate_age_from_birthdate(value: Any, params: Dict[str, Any]) -> Optional[int]:
        """Calculate age from birthdate"""
        if not isinstance(value, datetime):
            return None
        
        today = datetime.now(timezone.utc)
        age = today.year - value.year
        
        # Adjust if birthday hasn't occurred this year
        if today.month < value.month or (today.month == value.month and today.day < value.day):
            age -= 1
        
        return age
```

## Key Programming Concepts

### 1. **Rule-Based Transformation Pattern**
```python
@dataclass
class Rule:
    field: str
    transform: Callable
    condition: Optional[Callable] = None
    
def apply_rules(record: dict, rules: List[Rule]) -> dict:
    result = record.copy()
    for rule in rules:
        if rule.condition is None or rule.condition(result):
            result[rule.field] = rule.transform(result[rule.field])
    return result
```

### 2. **Pipeline Processing Pattern**
```python
async def process_pipeline(data: List[dict], transformers: List[Callable]) -> List[dict]:
    result = data
    for transformer in transformers:
        result = await transformer(result)
    return result
```

### 3. **Error Handling Strategies**
```python
def safe_transform(value, transformer, default=None, error_action="skip"):
    try:
        return transformer(value)
    except Exception as e:
        if error_action == "error":
            raise
        elif error_action == "default":
            return default
        else:  # skip
            return value
```

### 4. **Type Validation Pattern**
```python
def validate_type(value: Any, expected_type: type) -> bool:
    if isinstance(expected_type, tuple):
        return isinstance(value, expected_type)
    return isinstance(value, expected_type)
```

## Usage Examples

### Basic Transformation Setup
```python
from transformation.data_transformer import DataTransformer, TransformationRule

transformer = DataTransformer(schemas)

# Add transformation rules
rules = [
    TransformationRule(
        field_name="email",
        rule_type="clean",
        parameters={"transformation": "trim_whitespace"}
    ),
    TransformationRule(
        field_name="email",
        rule_type="validate",
        parameters={"validation_type": "email"},
        error_action="skip"
    ),
    TransformationRule(
        field_name="price",
        rule_type="convert",
        parameters={"target_type": "decimal"},
        error_action="default",
        default_value=Decimal('0.00')
    )
]

transformer.add_transformation_rules("Products", rules)

# Transform records
raw_records = [{"email": "  user@example.com  ", "price": "19.99"}]
transformed = await transformer.transform_records("Products", raw_records)
```

### Custom Transformation Rules
```python
# Custom validation function
def validate_product_code(value):
    return isinstance(value, str) and len(value) == 8 and value.isalnum()

# Custom transformation rule
custom_rule = TransformationRule(
    field_name="product_code",
    rule_type="validate",
    parameters={
        "validation_type": "custom",
        "validator": validate_product_code
    },
    error_action="error"
)

transformer.add_transformation_rules("Products", [custom_rule])
```

### Fluent Rule Building
```python
from transformation.data_transformer import TransformationRuleBuilder

rules = [
    TransformationRuleBuilder("name")
        .clean_with("trim_whitespace")
        .clean_with("normalize_case", case="title")
        .validate_as("length", min_length=1, max_length=100)
        .on_error("skip")
        .build(),
    
    TransformationRuleBuilder("birth_date")
        .convert_to("datetime", formats=["%Y-%m-%d", "%m/%d/%Y"])
        .on_error("default", datetime.now())
        .build()
]

transformer.add_transformation_rules("Customers", rules)
```

This file demonstrates enterprise-grade data transformation with comprehensive validation, cleaning, and conversion capabilities for OData processing pipelines.
