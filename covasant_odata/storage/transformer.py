"""Data transformer for SAP OData connector"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import structlog
import orjson
from pydantic import BaseModel, Field, validator
from datetime import datetime, timezone

from ..services.metadata import EntitySchema
from ..monitoring.metrics import get_metrics_collector

logger = structlog.get_logger(__name__)


class TransformedRecord(BaseModel):
    """Represents a transformed OData record"""
    
    entity_name: str
    record_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    transformed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@dataclass
class TransformationStats:
    """Statistics for transformation process"""
    records_processed: int = 0
    records_transformed: int = 0
    records_failed: int = 0
    transformation_errors: List[str] = None
    
    def __post_init__(self):
        if self.transformation_errors is None:
            self.transformation_errors = []


class DataTransformer:
    """Transforms SAP OData JSON responses into structured format"""
    
    def __init__(self, entity_schemas: Dict[str, EntitySchema]):
        self.entity_schemas = entity_schemas
        self.stats = TransformationStats()
    
    async def transform_odata_response(
        self,
        entity_name: str,
        response: Dict[str, Any]
    ) -> List[TransformedRecord]:
        """Transform OData JSON response into structured records"""
        
        start_time = asyncio.get_event_loop().time()
        metrics = get_metrics_collector()
        
        logger.info("Starting transformation",
                   entity_name=entity_name,
                   response_keys=list(response.keys()))
        
        try:
            # Get entity schema if available
            schema = self.entity_schemas.get(entity_name)
            
            # Extract records from response
            records = self._extract_records_from_response(response)
            
            logger.debug("Extracted records from response",
                        entity_name=entity_name,
                        record_count=len(records))
            
            # Transform each record
            transformed_records = []
            for record in records:
                try:
                    transformed = await self._transform_single_record(
                        entity_name, record, schema
                    )
                    transformed_records.append(transformed)
                    self.stats.records_transformed += 1
                    
                except Exception as e:
                    error_msg = f"Failed to transform record: {str(e)}"
                    logger.error("Record transformation failed", 
                               entity_name=entity_name,
                               error=error_msg)
                    self.stats.records_failed += 1
                    self.stats.transformation_errors.append(error_msg)
            
            self.stats.records_processed += len(records)
            
            # Record transformation metrics
            transformation_time = asyncio.get_event_loop().time() - start_time
            metrics.record_transformation(entity_name, transformation_time)
            
            logger.info("Transformation completed",
                       entity_name=entity_name,
                       input_records=len(records),
                       output_records=len(transformed_records),
                       transformation_time_seconds=round(transformation_time, 3))
            
            return transformed_records
            
        except Exception as e:
            logger.error("Failed to transform OData response",
                        entity_name=entity_name,
                        error=str(e))
            raise
    
    def _extract_records_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract record array from OData response structure"""
        
        # Handle different OData response formats
        if 'd' in response:
            # OData v2 format
            d_section = response['d']
            if 'results' in d_section:
                return d_section['results']
            elif isinstance(d_section, list):
                return d_section
            else:
                return [d_section]
        
        elif 'value' in response:
            # OData v4 format
            return response['value']
        
        elif isinstance(response, list):
            # Direct array
            return response
        
        else:
            # Single record
            return [response]
    
    async def _transform_single_record(
        self,
        entity_name: str,
        record: Dict[str, Any],
        schema: Optional[EntitySchema]
    ) -> TransformedRecord:
        """Transform a single record with schema validation"""
        
        # Generate record ID
        record_id = self._generate_record_id(record, schema)
        
        # Clean and normalize data
        cleaned_data = await self._clean_record_data(record, schema)
        
        # Extract metadata
        metadata = self._extract_metadata(record)
        
        return TransformedRecord(
            entity_name=entity_name,
            record_id=record_id,
            data=cleaned_data,
            metadata=metadata
        )
    
    def _generate_record_id(
        self, 
        record: Dict[str, Any], 
        schema: Optional[EntitySchema]
    ) -> str:
        """Generate unique record ID from key fields"""
        
        if schema and schema.keys:
            # Use entity key fields
            key_values = []
            for key_field in schema.keys:
                value = record.get(key_field, '')
                key_values.append(str(value))
            return '_'.join(key_values)
        
        else:
            # Fallback: use common ID fields
            for id_field in ['Id', 'ID', 'id', 'Key', 'key']:
                if id_field in record:
                    return str(record[id_field])
            
            # Last resort: hash of record content
            import hashlib
            content = orjson.dumps(record, sort_keys=True)
            return hashlib.md5(content).hexdigest()
    
    async def _clean_record_data(
        self,
        record: Dict[str, Any],
        schema: Optional[EntitySchema]
    ) -> Dict[str, Any]:
        """Clean and normalize record data"""
        
        cleaned = {}
        
        for field_name, field_value in record.items():
            # Skip OData metadata fields
            if field_name.startswith('__'):
                continue
            
            # Get field schema if available
            field_schema = None
            if schema and field_name in schema.properties:
                field_schema = schema.properties[field_name]
            
            # Clean field value
            cleaned_value = await self._clean_field_value(
                field_name, field_value, field_schema
            )
            
            if cleaned_value is not None:
                cleaned[field_name] = cleaned_value
        
        return cleaned
    
    async def _clean_field_value(
        self,
        field_name: str,
        field_value: Any,
        field_schema: Optional[Dict[str, Any]]
    ) -> Any:
        """Clean and normalize a single field value"""
        
        if field_value is None:
            return None
        
        # Handle OData-specific value formats
        if isinstance(field_value, dict):
            # Handle OData date/time values
            if '__edmType' in field_value:
                return self._parse_edm_value(field_value)
            
            # Handle deferred/navigation properties
            elif '__deferred' in field_value:
                return None  # Skip deferred properties
            
            # Recursively clean nested objects
            else:
                cleaned_nested = {}
                for k, v in field_value.items():
                    if not k.startswith('__'):
                        cleaned_nested[k] = await self._clean_field_value(k, v, None)
                return cleaned_nested
        
        elif isinstance(field_value, list):
            # Clean array values
            cleaned_array = []
            for item in field_value:
                cleaned_item = await self._clean_field_value(field_name, item, field_schema)
                if cleaned_item is not None:
                    cleaned_array.append(cleaned_item)
            return cleaned_array
        
        elif isinstance(field_value, str):
            # Clean string values
            return self._clean_string_value(field_value, field_schema)
        
        else:
            # Return primitive values as-is
            return field_value
    
    def _parse_edm_value(self, edm_value: Dict[str, Any]) -> Any:
        """Parse OData EDM typed values"""
        
        edm_type = edm_value.get('__edmType', '')
        value = edm_value.get('value') or edm_value.get('Value')
        
        if 'DateTime' in edm_type:
            # Parse OData datetime
            if isinstance(value, str):
                try:
                    # Handle different datetime formats
                    if value.startswith('/Date(') and value.endswith(')/'):
                        # .NET JSON date format
                        timestamp = int(value[6:-2])
                        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                    else:
                        # ISO format
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning("Failed to parse datetime", value=value)
                    return value
        
        elif 'Decimal' in edm_type or 'Double' in edm_type:
            # Parse numeric values
            try:
                return float(value) if value is not None else None
            except (ValueError, TypeError):
                return value
        
        elif 'Int' in edm_type:
            # Parse integer values
            try:
                return int(value) if value is not None else None
            except (ValueError, TypeError):
                return value
        
        return value
    
    # def _clean_string_value(
    #     self, 
    #     value: str, 
    #     field_schema: Optional[Dict[str, Any]]
    # ) -> str:
    #     """Clean string values"""
        
    #     # Trim whitespace
    #     cleaned = value.strip()
        
    #     # Handle empty strings
    #     if not cleaned:
    #         return None if field_schema and field_schema.get('nullable', True) else ''
        
    #     # Truncate if max length is specified
    #     # if field_schema and 'max_length' in field_schema:
    #     #     max_length = field_schema['max_length']
    #     #     if max_length and len(cleaned) > max_length:
    #     #         cleaned = cleaned[:max_length]
    #     # Truncate if max length is specified
    #     if field_schema and 'max_length' in field_schema:
    #         try:
    #             max_length = int(field_schema['max_length'])
    #             if max_length and len(cleaned) > max_length:
    #                 cleaned = cleaned[:max_length]
    #         except (ValueError, TypeError):
    #             # Log a warning if max_length is not a valid integer
    #             logger.warning("Invalid max_length value in schema", 
    #                         value=field_schema['max_length'])
    #             logger.warning("String truncated to max length",
    #                          original_length=len(value),
    #                          max_length=max_length)
        
    #     return cleaned
    
    def _clean_string_value(
        self, 
        value: str, 
        field_schema: Optional[Dict[str, Any]]
        ) -> str:
        """Clean string values"""
        
        # Trim whitespace
        cleaned = value.strip()
        
        # Handle empty strings
        if not cleaned:
            return None if field_schema and field_schema.get('nullable', True) else ''
        
        # Truncate if max length is specified in the schema
        if field_schema and 'max_length' in field_schema:
            max_length_value = field_schema.get('max_length')

            # Ensure the max_length value is a valid number before using it
            if max_length_value is not None:
                try:
                    max_length = int(max_length_value)
                    if max_length > 0 and len(cleaned) > max_length:
                        cleaned = cleaned[:max_length]
                        logger.warning("String truncated to max length",
                                        original_length=len(value),
                                        max_length=max_length)
                except (ValueError, TypeError):
                    # Log a warning if the schema value is not a valid integer
                    logger.warning("Invalid max_length value in schema",
                                    value=max_length_value)

        return cleaned
    
    def _extract_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract OData metadata from record"""
        
        metadata = {}
        
        for key, value in record.items():
            if key.startswith('__'):
                # OData metadata field
                metadata[key] = value
        
        return metadata
    
    async def transform_batch(
        self, 
        batch_data: List[tuple[str, Dict[str, Any]]]
    ) -> List[TransformedRecord]:
        """Transform a batch of records from different entities"""
        
        all_transformed = []
        
        for entity_name, odata_response in batch_data:
            transformed = await self.transform_odata_response(entity_name, odata_response)
            all_transformed.extend(transformed)
        
        return all_transformed
    
    def get_transformation_stats(self) -> TransformationStats:
        """Get transformation statistics"""
        return self.stats
    
    def reset_stats(self):
        """Reset transformation statistics"""
        self.stats = TransformationStats()
