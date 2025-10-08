"""BigQuery storage implementation for SAP OData connector"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import orjson

from .transformer import TransformedRecord

logger = structlog.get_logger(__name__)


@dataclass
class BigQueryConfig:
    """Configuration for BigQuery storage"""
    project_id: str
    dataset_id: str
    location: str = "US"
    write_disposition: str = "WRITE_APPEND"
    create_disposition: str = "CREATE_IF_NEEDED"


class BigQueryStorage:
    """Handles structured data storage in BigQuery"""
    
    def __init__(self, config: BigQueryConfig):
        self.config = config
        self.client = bigquery.Client(project=config.project_id)
        self.dataset_ref = self.client.dataset(config.dataset_id)
        self._table_schemas: Dict[str, List[bigquery.SchemaField]] = {}
    
    async def store_records(
        self, 
        entity_name: str, 
        records: List[TransformedRecord]
    ) -> bool:
        """Store transformed records in BigQuery"""
        
        if not records:
            logger.info("No records to store", entity_name=entity_name)
            return True
        
        logger.info("Storing records in BigQuery", 
                   entity_name=entity_name,
                   record_count=len(records))
        
        try:
            # Ensure table exists
            table_ref = await self._ensure_table_exists(entity_name, records[0])
            
            # Prepare rows for insertion
            rows_to_insert = []
            for record in records:
                row = self._prepare_row_for_bigquery(record)
                rows_to_insert.append(row)
            
            # Insert rows
            errors = self.client.insert_rows_json(table_ref, rows_to_insert)
            
            if errors:
                logger.error("BigQuery insertion errors", 
                           entity_name=entity_name,
                           errors=errors)
                return False
            
            logger.info("Successfully stored records", 
                       entity_name=entity_name,
                       stored_count=len(records))
            return True
            
        except GoogleCloudError as e:
            logger.error("BigQuery storage failed", 
                        entity_name=entity_name,
                        error=str(e))
            return False
    
    async def _ensure_table_exists(
        self, 
        entity_name: str, 
        sample_record: TransformedRecord
    ) -> bigquery.TableReference:
        """Ensure BigQuery table exists with proper schema"""
        
        table_id = self._sanitize_table_name(entity_name)
        table_ref = self.dataset_ref.table(table_id)
        
        try:
            # Try to get existing table
            table = self.client.get_table(table_ref)
            logger.debug("Using existing table", table_id=table_id)
            return table_ref
            
        except Exception:
            # Table doesn't exist, create it
            logger.info("Creating new BigQuery table", table_id=table_id)
            
            schema = self._generate_schema_from_record(sample_record)
            table = bigquery.Table(table_ref, schema=schema)
            
            # Set table properties
            table.description = f"SAP OData data for entity: {entity_name}"
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="transformed_at"
            )
            
            created_table = self.client.create_table(table)
            logger.info("Created BigQuery table", table_id=table_id)
            
            return created_table.reference
    
    def _sanitize_table_name(self, entity_name: str) -> str:
        """Sanitize entity name for BigQuery table naming"""
        # Replace invalid characters and ensure valid naming
        sanitized = entity_name.replace('-', '_').replace(' ', '_')
        # Ensure it starts with letter or underscore
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
            sanitized = f"entity_{sanitized}"
        return sanitized.lower()
    
    def _generate_schema_from_record(self, record: TransformedRecord) -> List[bigquery.SchemaField]:
        """Generate BigQuery schema from a sample record"""
        
        schema_fields = [
            bigquery.SchemaField("entity_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("record_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("transformed_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        # Add fields from record data
        data_fields = self._infer_schema_from_data(record.data)
        schema_fields.extend(data_fields)
        
        # Add metadata as JSON
        schema_fields.append(
            bigquery.SchemaField("metadata", "JSON", mode="NULLABLE")
        )
        
        return schema_fields
    
    def _infer_schema_from_data(self, data: Dict[str, Any], prefix: str = "") -> List[bigquery.SchemaField]:
        """Infer BigQuery schema from record data"""
        
        fields = []
        
        for field_name, field_value in data.items():
            full_field_name = f"{prefix}{field_name}" if prefix else field_name
            
            # Sanitize field name
            sanitized_name = self._sanitize_field_name(full_field_name)
            
            if field_value is None:
                # Default to string for null values
                field_type = "STRING"
                mode = "NULLABLE"
            
            elif isinstance(field_value, bool):
                field_type = "BOOLEAN"
                mode = "NULLABLE"
            
            elif isinstance(field_value, int):
                field_type = "INTEGER"
                mode = "NULLABLE"
            
            elif isinstance(field_value, float):
                field_type = "FLOAT"
                mode = "NULLABLE"
            
            elif isinstance(field_value, str):
                field_type = "STRING"
                mode = "NULLABLE"
            
            elif isinstance(field_value, dict):
                # Store complex objects as JSON
                field_type = "JSON"
                mode = "NULLABLE"
            
            elif isinstance(field_value, list):
                # Handle arrays
                if field_value and isinstance(field_value[0], dict):
                    # Array of objects - store as JSON
                    field_type = "JSON"
                else:
                    # Array of primitives - store as JSON for simplicity
                    field_type = "JSON"
                mode = "REPEATED"
            
            else:
                # Default to string for unknown types
                field_type = "STRING"
                mode = "NULLABLE"
            
            fields.append(bigquery.SchemaField(sanitized_name, field_type, mode=mode))
        
        return fields
    
    def _sanitize_field_name(self, field_name: str) -> str:
        """Sanitize field name for BigQuery"""
        # Replace invalid characters
        sanitized = field_name.replace('-', '_').replace(' ', '_').replace('.', '_')
        # Ensure valid naming
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
            sanitized = f"field_{sanitized}"
        return sanitized.lower()
    
    def _prepare_row_for_bigquery(self, record: TransformedRecord) -> Dict[str, Any]:
        """Prepare record for BigQuery insertion"""
        
        row = {
            "entity_name": record.entity_name,
            "record_id": record.record_id,
            "transformed_at": record.transformed_at.isoformat(),
            "metadata": record.metadata
        }
        
        # Add data fields with sanitized names
        for field_name, field_value in record.data.items():
            sanitized_name = self._sanitize_field_name(field_name)
            row[sanitized_name] = field_value
        
        return row
    
    async def create_dataset_if_not_exists(self) -> bool:
        """Create BigQuery dataset if it doesn't exist"""
        
        try:
            # Try to get existing dataset
            self.client.get_dataset(self.dataset_ref)
            logger.debug("Using existing dataset", dataset_id=self.config.dataset_id)
            return True
            
        except Exception:
            # Dataset doesn't exist, create it
            logger.info("Creating BigQuery dataset", dataset_id=self.config.dataset_id)
            
            dataset = bigquery.Dataset(self.dataset_ref)
            dataset.location = self.config.location
            dataset.description = "SAP OData connector structured storage"
            
            created_dataset = self.client.create_dataset(dataset)
            logger.info("Created BigQuery dataset", dataset_id=created_dataset.dataset_id)
            return True
    
    async def get_table_info(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a BigQuery table"""
        
        table_id = self._sanitize_table_name(entity_name)
        table_ref = self.dataset_ref.table(table_id)
        
        try:
            table = self.client.get_table(table_ref)
            
            return {
                "table_id": table.table_id,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "schema_fields": len(table.schema)
            }
            
        except Exception as e:
            logger.warning("Failed to get table info", 
                         entity_name=entity_name,
                         error=str(e))
            return None
    
    async def query_records(
        self, 
        entity_name: str, 
        limit: int = 100,
        where_clause: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query records from BigQuery table"""
        
        table_id = self._sanitize_table_name(entity_name)
        
        query = f"""
        SELECT *
        FROM `{self.config.project_id}.{self.config.dataset_id}.{table_id}`
        """
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        query += f" LIMIT {limit}"
        
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            
            records = []
            for row in results:
                records.append(dict(row))
            
            return records
            
        except Exception as e:
            logger.error("Query failed", 
                        entity_name=entity_name,
                        error=str(e))
            return []
