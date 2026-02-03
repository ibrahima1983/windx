"""Base schemas and common types for product definitions.

This module provides the foundation schemas that are shared across
different product definition scopes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field

__all__ = [
    "BaseEntityCreate",
    "BaseEntityUpdate", 
    "BaseEntityResponse",
    "BaseResponse",
    "ErrorResponse",
    "MetadataField"
]


# ============================================================================
# Common Types
# ============================================================================

class MetadataField(BaseModel):
    """Schema for metadata field definitions."""
    
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type (text, number, boolean, select)")
    label: str = Field(..., description="Display label")
    required: bool = Field(False, description="Whether field is required")
    options: Optional[List[str]] = Field(None, description="Options for select fields")
    min_value: Optional[float] = Field(None, description="Minimum value for number fields")
    max_value: Optional[float] = Field(None, description="Maximum value for number fields")
    default_value: Optional[Any] = Field(None, description="Default value")


# ============================================================================
# Base Entity Schemas
# ============================================================================

class BaseEntityCreate(BaseModel):
    """Base schema for creating entities."""
    
    entity_type: str = Field(..., description="Entity type (varies by scope)")
    name: str = Field(..., min_length=1, max_length=200, description="Entity name")
    description: Optional[str] = Field(None, description="Entity description")
    image_url: Optional[str] = Field(None, max_length=500, description="Image URL")
    price_from: Optional[Decimal] = Field(None, ge=0, description="Base price")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BaseEntityUpdate(BaseModel):
    """Base schema for updating entities."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Entity name")
    description: Optional[str] = Field(None, description="Entity description")
    image_url: Optional[str] = Field(None, max_length=500, description="Image URL")
    price_from: Optional[Decimal] = Field(None, ge=0, description="Base price")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BaseEntityResponse(BaseModel):
    """Base schema for entity responses."""
    
    id: int = Field(..., description="Entity ID")
    name: str = Field(..., description="Entity name")
    description: Optional[str] = Field(None, description="Entity description")
    image_url: Optional[str] = Field(None, description="Image URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


# ============================================================================
# Base Response Schemas
# ============================================================================

class BaseResponse(BaseModel):
    """Base response schema."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")


class ErrorResponse(BaseResponse):
    """Error response schema."""
    
    success: bool = Field(False, description="Always false for errors")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


# ============================================================================
# Scope Metadata Schemas
# ============================================================================

class ScopeEntityConfig(BaseModel):
    """Configuration for a scope entity type."""
    
    label: str = Field(..., description="Display label")
    icon: Optional[str] = Field(None, description="Icon class")
    description: Optional[str] = Field(None, description="Entity description")
    metadata_fields: List[MetadataField] = Field(default_factory=list, description="Metadata field definitions")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")


class ScopeMetadata(BaseModel):
    """Metadata for a product definition scope."""
    
    scope: str = Field(..., description="Scope name")
    label: str = Field(..., description="Display label")
    description: Optional[str] = Field(None, description="Scope description")
    entities: Dict[str, ScopeEntityConfig] = Field(default_factory=dict, description="Entity configurations")
    supports_hierarchy: bool = Field(False, description="Whether scope supports hierarchical relationships")
    supports_composition: bool = Field(False, description="Whether scope supports compositional relationships")
    supports_calculations: bool = Field(False, description="Whether scope supports calculations")


# ============================================================================
# Common Request/Response Patterns
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")


class SortParams(BaseModel):
    """Sorting parameters."""
    
    sort_by: str = Field("name", description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class FilterParams(BaseModel):
    """Filtering parameters."""
    
    search: Optional[str] = Field(None, description="Search term")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    has_image: Optional[bool] = Field(None, description="Filter by image presence")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")


class BulkOperationRequest(BaseModel):
    """Request for bulk operations."""
    
    entity_ids: List[int] = Field(..., min_items=1, description="List of entity IDs")
    operation: str = Field(..., description="Operation to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")


class BulkOperationResponse(BaseResponse):
    """Response for bulk operations."""
    
    processed_count: int = Field(..., description="Number of entities processed")
    failed_count: int = Field(..., description="Number of entities that failed")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="List of errors")