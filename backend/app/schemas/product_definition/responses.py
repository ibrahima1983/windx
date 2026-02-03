"""Common response schemas for product definitions.

This module provides standardized response schemas that are used
across different product definition scopes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Generic, TypeVar
from decimal import Decimal

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

from .base import BaseResponse, BaseEntityResponse

__all__ = [
    "EntityListResponse",
    "PathListResponse", 
    "ComponentListResponse",
    "PaginatedResponse",
    "OperationResponse",
    "ValidationResponse",
    "HealthCheckResponse"
]

# Type variable for generic responses
T = TypeVar('T')


# ============================================================================
# Generic Response Schemas
# ============================================================================

class PaginatedResponse(GenericModel, Generic[T]):
    """Generic paginated response schema."""
    
    success: bool = Field(True, description="Operation success status")
    items: List[T] = Field(..., description="List of items")
    total_count: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class OperationResponse(BaseResponse):
    """Response for operations that modify data."""
    
    affected_count: int = Field(0, description="Number of items affected")
    details: Optional[Dict[str, Any]] = Field(None, description="Operation details")
    warnings: List[str] = Field(default_factory=list, description="Operation warnings")


class ValidationResponse(BaseResponse):
    """Response for validation operations."""
    
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


# ============================================================================
# Entity List Responses
# ============================================================================

class EntityListResponse(BaseResponse):
    """Response for entity list operations."""
    
    entities: List[BaseEntityResponse] = Field(
        default_factory=list,
        description="List of entities"
    )
    total_count: int = Field(0, description="Total number of entities")
    entity_type: Optional[str] = Field(None, description="Type of entities in list")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the entities"
    )


class EntityStatsResponse(BaseResponse):
    """Response for entity statistics."""
    
    total_entities: int = Field(..., description="Total number of entities")
    entities_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Entity count by type"
    )
    recent_activity: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent entity activity"
    )
    trends: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entity trends and analytics"
    )


# ============================================================================
# Profile-Specific Responses
# ============================================================================

class PathListResponse(BaseResponse):
    """Response for profile path list operations."""
    
    paths: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of dependency paths"
    )
    total_count: int = Field(0, description="Total number of paths")
    hierarchy_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Information about the hierarchy structure"
    )


class HierarchyResponse(BaseResponse):
    """Response for hierarchy operations."""
    
    hierarchy: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hierarchy structure"
    )
    levels: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Hierarchy levels"
    )
    entity_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Entity counts by level"
    )


# ============================================================================
# Glazing-Specific Responses
# ============================================================================

class ComponentListResponse(BaseResponse):
    """Response for glazing component list operations."""
    
    components: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Components grouped by type"
    )
    total_count: int = Field(0, description="Total number of components")
    component_types: List[str] = Field(
        default_factory=list,
        description="Available component types"
    )


class GlazingUnitListResponse(BaseResponse):
    """Response for glazing unit list operations."""
    
    units: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of glazing units"
    )
    total_count: int = Field(0, description="Total number of units")
    unit_types: List[str] = Field(
        default_factory=list,
        description="Available unit types"
    )
    performance_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance statistics"
    )


class CalculationListResponse(BaseResponse):
    """Response for calculation history operations."""
    
    calculations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of calculations"
    )
    total_count: int = Field(0, description="Total number of calculations")
    popular_configurations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most popular configurations"
    )


# ============================================================================
# System Responses
# ============================================================================

class HealthCheckResponse(BaseResponse):
    """Response for system health checks."""
    
    status: str = Field(..., description="Overall system status")
    services: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Status of individual services"
    )
    database: Dict[str, Any] = Field(
        default_factory=dict,
        description="Database status and metrics"
    )
    cache: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cache status and metrics"
    )
    timestamp: str = Field(..., description="Health check timestamp")


class ScopeListResponse(BaseResponse):
    """Response for available scopes."""
    
    scopes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Available product definition scopes"
    )
    total_count: int = Field(0, description="Total number of scopes")
    active_scopes: List[str] = Field(
        default_factory=list,
        description="Currently active scopes"
    )


class MetricsResponse(BaseResponse):
    """Response for system metrics."""
    
    performance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance metrics"
    )
    usage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Usage statistics"
    )
    errors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Error statistics"
    )
    trends: Dict[str, Any] = Field(
        default_factory=dict,
        description="Trend analysis"
    )


# ============================================================================
# Bulk Operation Responses
# ============================================================================

class BulkCreateResponse(BaseResponse):
    """Response for bulk create operations."""
    
    created_count: int = Field(0, description="Number of items created")
    failed_count: int = Field(0, description="Number of items that failed")
    created_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Successfully created items"
    )
    failed_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Items that failed to create"
    )


class BulkUpdateResponse(BaseResponse):
    """Response for bulk update operations."""
    
    updated_count: int = Field(0, description="Number of items updated")
    failed_count: int = Field(0, description="Number of items that failed")
    updated_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Successfully updated items"
    )
    failed_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Items that failed to update"
    )


class BulkDeleteResponse(BaseResponse):
    """Response for bulk delete operations."""
    
    deleted_count: int = Field(0, description="Number of items deleted")
    failed_count: int = Field(0, description="Number of items that failed")
    deleted_ids: List[int] = Field(
        default_factory=list,
        description="IDs of successfully deleted items"
    )
    failed_ids: List[int] = Field(
        default_factory=list,
        description="IDs of items that failed to delete"
    )


# ============================================================================
# Export/Import Responses
# ============================================================================

class ExportResponse(BaseResponse):
    """Response for export operations."""
    
    export_id: str = Field(..., description="Unique export identifier")
    file_url: Optional[str] = Field(None, description="URL to download exported file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    format: str = Field(..., description="Export format")
    exported_count: int = Field(0, description="Number of items exported")
    expires_at: Optional[str] = Field(None, description="Export expiration timestamp")


class ImportResponse(BaseResponse):
    """Response for import operations."""
    
    import_id: str = Field(..., description="Unique import identifier")
    processed_count: int = Field(0, description="Number of items processed")
    imported_count: int = Field(0, description="Number of items imported")
    updated_count: int = Field(0, description="Number of items updated")
    skipped_count: int = Field(0, description="Number of items skipped")
    failed_count: int = Field(0, description="Number of items that failed")
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Import errors with details"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Import warnings"
    )