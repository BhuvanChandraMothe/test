"""
Advanced OData Query Builder for Complex Queries
Supports $expand, $select, $orderby, $filter, aggregation, and complex operations
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class AggregateFunction(Enum):
    """OData aggregation functions"""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "countdistinct"
    COUNT_ALL = "$count"


class FilterOperator(Enum):
    """OData filter operators"""
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    AND = "and"
    OR = "or"
    NOT = "not"
    CONTAINS = "contains"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    IN = "in"


@dataclass
class ExpandClause:
    """Represents an $expand clause"""
    property_name: str
    select_fields: Optional[List[str]] = None
    filter_condition: Optional[str] = None
    orderby: Optional[str] = None
    top: Optional[int] = None
    nested_expand: Optional[List['ExpandClause']] = None
    
    def to_string(self) -> str:
        """Convert expand clause to OData string"""
        expand_str = self.property_name
        
        options = []
        if self.select_fields:
            options.append(f"$select={','.join(self.select_fields)}")
        if self.filter_condition:
            options.append(f"$filter={self.filter_condition}")
        if self.orderby:
            options.append(f"$orderby={self.orderby}")
        if self.top:
            options.append(f"$top={self.top}")
        if self.nested_expand:
            nested_expands = ','.join([exp.to_string() for exp in self.nested_expand])
            options.append(f"$expand={nested_expands}")
        
        if options:
            expand_str += f"({';'.join(options)})"
        
        return expand_str


@dataclass
class AggregateClause:
    """Represents aggregation operations"""
    field: str
    function: AggregateFunction
    alias: Optional[str] = None
    
    def to_string(self) -> str:
        """Convert aggregate clause to OData string"""
        if self.function == AggregateFunction.COUNT_ALL:
            return "$count as TotalCount"
        
        result = f"{self.field} with {self.function.value}"
        if self.alias:
            result += f" as {self.alias}"
        return result


@dataclass
class GroupByClause:
    """Represents grouping operations"""
    fields: List[str]
    aggregates: List[AggregateClause] = field(default_factory=list)
    
    def to_string(self) -> str:
        """Convert groupby clause to OData string"""
        group_fields = ','.join(self.fields)
        
        if self.aggregates:
            agg_strings = [agg.to_string() for agg in self.aggregates]
            return f"({group_fields}),aggregate({','.join(agg_strings)})"
        
        return f"({group_fields})"


class ODataQueryBuilder:
    """Advanced OData Query Builder"""
    
    def __init__(self, entity_name: str):
        self.entity_name = entity_name
        self.select_fields: List[str] = []
        self.expand_clauses: List[ExpandClause] = []
        self.filter_conditions: List[str] = []
        self.orderby_clauses: List[str] = []
        self.groupby_clause: Optional[GroupByClause] = None
        self.top_value: Optional[int] = None
        self.skip_value: Optional[int] = None
        self.count_enabled: bool = False
        self.apply_transformations: List[str] = []
        self.custom_params: Dict[str, str] = {}
    
    def select(self, *fields: str) -> 'ODataQueryBuilder':
        """Add fields to $select clause"""
        self.select_fields.extend(fields)
        return self
    
    def expand(self, expand_clause: Union[str, ExpandClause]) -> 'ODataQueryBuilder':
        """Add $expand clause"""
        if isinstance(expand_clause, str):
            self.expand_clauses.append(ExpandClause(property_name=expand_clause))
        else:
            self.expand_clauses.append(expand_clause)
        return self
    
    def expand_with_select(self, property_name: str, select_fields: List[str]) -> 'ODataQueryBuilder':
        """Add $expand with nested $select"""
        expand_clause = ExpandClause(property_name=property_name, select_fields=select_fields)
        self.expand_clauses.append(expand_clause)
        return self
    
    def expand_with_filter(self, property_name: str, filter_condition: str) -> 'ODataQueryBuilder':
        """Add $expand with nested $filter"""
        expand_clause = ExpandClause(property_name=property_name, filter_condition=filter_condition)
        self.expand_clauses.append(expand_clause)
        return self
    
    def expand_nested(self, property_name: str, nested_expands: List[ExpandClause]) -> 'ODataQueryBuilder':
        """Add nested $expand clauses"""
        expand_clause = ExpandClause(property_name=property_name, nested_expand=nested_expands)
        self.expand_clauses.append(expand_clause)
        return self
    
    def filter(self, condition: str) -> 'ODataQueryBuilder':
        """Add $filter condition"""
        self.filter_conditions.append(condition)
        return self
    
    def filter_equals(self, field: str, value: Any) -> 'ODataQueryBuilder':
        """Add equals filter condition"""
        if isinstance(value, str):
            condition = f"{field} eq '{value}'"
        else:
            condition = f"{field} eq {value}"
        return self.filter(condition)
    
    def filter_contains(self, field: str, value: str) -> 'ODataQueryBuilder':
        """Add contains filter condition"""
        condition = f"contains({field}, '{value}')"
        return self.filter(condition)
    
    def filter_in(self, field: str, values: List[Any]) -> 'ODataQueryBuilder':
        """Add 'in' filter condition"""
        if isinstance(values[0], str):
            value_list = ','.join([f"'{v}'" for v in values])
        else:
            value_list = ','.join([str(v) for v in values])
        condition = f"{field} in ({value_list})"
        return self.filter(condition)
    
    def filter_date_range(self, field: str, start_date: str, end_date: str) -> 'ODataQueryBuilder':
        """Add date range filter"""
        condition = f"{field} ge {start_date} and {field} le {end_date}"
        return self.filter(condition)
    
    def filter_complex(self, field: str, operator: FilterOperator, value: Any, 
                      combine_with: Optional[FilterOperator] = None) -> 'ODataQueryBuilder':
        """Add complex filter with operators"""
        if isinstance(value, str):
            condition = f"{field} {operator.value} '{value}'"
        else:
            condition = f"{field} {operator.value} {value}"
        
        if combine_with and self.filter_conditions:
            # Combine with previous condition
            prev_condition = self.filter_conditions.pop()
            condition = f"{prev_condition} {combine_with.value} {condition}"
        
        return self.filter(condition)
    
    def orderby(self, field: str, descending: bool = False) -> 'ODataQueryBuilder':
        """Add $orderby clause"""
        order_clause = f"{field} {'desc' if descending else 'asc'}"
        self.orderby_clauses.append(order_clause)
        return self
    
    def orderby_multiple(self, fields: List[tuple]) -> 'ODataQueryBuilder':
        """Add multiple orderby clauses. fields = [(field_name, is_descending), ...]"""
        for field, descending in fields:
            self.orderby(field, descending)
        return self
    
    def top(self, count: int) -> 'ODataQueryBuilder':
        """Add $top clause"""
        self.top_value = count
        return self
    
    def skip(self, count: int) -> 'ODataQueryBuilder':
        """Add $skip clause"""
        self.skip_value = count
        return self
    
    def count(self, enabled: bool = True) -> 'ODataQueryBuilder':
        """Enable/disable $count"""
        self.count_enabled = enabled
        return self
    
    def groupby(self, *fields: str) -> 'ODataQueryBuilder':
        """Add $apply groupby transformation"""
        self.groupby_clause = GroupByClause(fields=list(fields))
        return self
    
    def aggregate(self, field: str, function: AggregateFunction, alias: Optional[str] = None) -> 'ODataQueryBuilder':
        """Add aggregation to groupby"""
        if not self.groupby_clause:
            raise ValueError("Must call groupby() before aggregate()")
        
        agg_clause = AggregateClause(field=field, function=function, alias=alias)
        self.groupby_clause.aggregates.append(agg_clause)
        return self
    
    def sum(self, field: str, alias: Optional[str] = None) -> 'ODataQueryBuilder':
        """Add sum aggregation"""
        return self.aggregate(field, AggregateFunction.SUM, alias)
    
    def average(self, field: str, alias: Optional[str] = None) -> 'ODataQueryBuilder':
        """Add average aggregation"""
        return self.aggregate(field, AggregateFunction.AVERAGE, alias)
    
    def min_value(self, field: str, alias: Optional[str] = None) -> 'ODataQueryBuilder':
        """Add min aggregation"""
        return self.aggregate(field, AggregateFunction.MIN, alias)
    
    def max_value(self, field: str, alias: Optional[str] = None) -> 'ODataQueryBuilder':
        """Add max aggregation"""
        return self.aggregate(field, AggregateFunction.MAX, alias)
    
    def count_distinct(self, field: str, alias: Optional[str] = None) -> 'ODataQueryBuilder':
        """Add count distinct aggregation"""
        return self.aggregate(field, AggregateFunction.COUNT, alias)
    
    def apply_transformation(self, transformation: str) -> 'ODataQueryBuilder':
        """Add custom $apply transformation"""
        self.apply_transformations.append(transformation)
        return self
    
    def custom_parameter(self, key: str, value: str) -> 'ODataQueryBuilder':
        """Add custom query parameter"""
        self.custom_params[key] = value
        return self
    
    def build_url(self, base_url: str) -> str:
        """Build complete OData URL"""
        url = f"{base_url}/{self.entity_name}"
        query_params = self.build_query_params()
        
        if query_params:
            url += "?" + "&".join([f"{k}={v}" for k, v in query_params.items()])
        
        return url
    
    def build_query_params(self) -> Dict[str, str]:
        """Build query parameters dictionary"""
        params = {}
        
        # $select
        if self.select_fields:
            params["$select"] = ",".join(self.select_fields)
        
        # $expand
        if self.expand_clauses:
            expand_strings = [exp.to_string() for exp in self.expand_clauses]
            params["$expand"] = ",".join(expand_strings)
        
        # $filter
        if self.filter_conditions:
            if len(self.filter_conditions) == 1:
                params["$filter"] = self.filter_conditions[0]
            else:
                # Combine multiple filters with 'and'
                params["$filter"] = " and ".join([f"({cond})" for cond in self.filter_conditions])
        
        # $orderby
        if self.orderby_clauses:
            params["$orderby"] = ",".join(self.orderby_clauses)
        
        # $top
        if self.top_value:
            params["$top"] = str(self.top_value)
        
        # $skip
        if self.skip_value:
            params["$skip"] = str(self.skip_value)
        
        # $count
        if self.count_enabled:
            params["$count"] = "true"
        
        # $apply (for groupby and aggregations)
        if self.groupby_clause or self.apply_transformations:
            apply_parts = []
            
            if self.groupby_clause:
                apply_parts.append(f"groupby{self.groupby_clause.to_string()}")
            
            apply_parts.extend(self.apply_transformations)
            
            if apply_parts:
                params["$apply"] = "/".join(apply_parts)
        
        # Custom parameters
        params.update(self.custom_params)
        
        return params
    
    def build_query_string(self) -> str:
        """Build query string portion of URL"""
        params = self.build_query_params()
        if params:
            return "&".join([f"{k}={v}" for k, v in params.items()])
        return ""
    
    def clone(self) -> 'ODataQueryBuilder':
        """Create a copy of this query builder"""
        new_builder = ODataQueryBuilder(self.entity_name)
        new_builder.select_fields = self.select_fields.copy()
        new_builder.expand_clauses = self.expand_clauses.copy()
        new_builder.filter_conditions = self.filter_conditions.copy()
        new_builder.orderby_clauses = self.orderby_clauses.copy()
        new_builder.groupby_clause = self.groupby_clause
        new_builder.top_value = self.top_value
        new_builder.skip_value = self.skip_value
        new_builder.count_enabled = self.count_enabled
        new_builder.apply_transformations = self.apply_transformations.copy()
        new_builder.custom_params = self.custom_params.copy()
        return new_builder
    
    def reset(self) -> 'ODataQueryBuilder':
        """Reset all query parameters"""
        self.select_fields.clear()
        self.expand_clauses.clear()
        self.filter_conditions.clear()
        self.orderby_clauses.clear()
        self.groupby_clause = None
        self.top_value = None
        self.skip_value = None
        self.count_enabled = False
        self.apply_transformations.clear()
        self.custom_params.clear()
        return self
    
    def __str__(self) -> str:
        """String representation of the query"""
        query_string = self.build_query_string()
        return f"{self.entity_name}?{query_string}" if query_string else self.entity_name


# Convenience functions for common query patterns

def create_product_query_with_category() -> ODataQueryBuilder:
    """Example: Products with expanded Category information"""
    return (ODataQueryBuilder("Products")
            .select("ProductID", "ProductName", "UnitPrice", "UnitsInStock")
            .expand_with_select("Category", ["CategoryID", "CategoryName", "Description"])
            .filter("UnitPrice gt 20")
            .orderby("ProductName"))


def create_order_summary_query() -> ODataQueryBuilder:
    """Example: Order summary with aggregations"""
    return (ODataQueryBuilder("Orders")
            .groupby("CustomerID", "OrderDate")
            .sum("Freight", "TotalFreight")
            .count_distinct("OrderID", "OrderCount")
            .filter("OrderDate ge 2023-01-01"))


def create_customer_orders_query() -> ODataQueryBuilder:
    """Example: Customers with their orders and order details"""
    order_details_expand = ExpandClause(
        property_name="Order_Details",
        select_fields=["ProductID", "Quantity", "UnitPrice"],
        expand_clause=ExpandClause(property_name="Product", select_fields=["ProductName"])
    )
    
    orders_expand = ExpandClause(
        property_name="Orders",
        select_fields=["OrderID", "OrderDate", "Freight"],
        nested_expand=[order_details_expand]
    )
    
    return (ODataQueryBuilder("Customers")
            .select("CustomerID", "CompanyName", "ContactName")
            .expand(orders_expand)
            .filter("Country eq 'USA'")
            .orderby("CompanyName"))
