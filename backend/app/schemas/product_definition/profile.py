"""Profile-specific schemas for product definitions.

This module provides schemas for the profile scope which handles
hierarchical dependencies (Company → Material → Opening System → System Series → Color).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal

from pydantic import BaseModel, Field

from .base import BaseEntityCreate, BaseEntityUpdate, BaseEntityResponse, BaseResponse

__all__ = [
    "ProfileEntityCreate",
    "ProfileEntityUpdate",
    "ProfileEntityResponse",
    "ProfilePathCreate",
    "ProfilePathDelete",
    "ProfilePathResponse",
    "ProfileDependentOptionsRequest",
    "ProfileDependentOptionsResponse",
    "ProfileScopeResponse"
]


# ============================================================================
# Profile Entity Schemas
# ============================================================================

class ProfileEntityCreate(BaseEntityCreate):
    """Schema for creating profile entities."""
    
    entity_type: str = Field(
        ..., 
        pattern="^(company|material|opening_system|system_series|color)$",
        description="Type of profile entity"
    )
    price_from: Optional[Decimal] = Field(
        None, 
        ge=0, 
        description="Base price for this entity"
    )


class ProfileEntityUpdate(BaseEntityUpdate):
    """Schema for updating profile entities."""
    
    price_from: Optional[Decimal] = Field(
        None, 
        ge=0, 
        description="Base price for this entity"
    )


class ProfileEntityResponse(BaseEntityResponse):
    """Schema for profile entity responses."""
    
    entity_type: str = Field(..., description="Type of profile entity")
    price_from: Optional[Decimal] = Field(None, description="Base price for this entity")
    ltree_path: Optional[str] = Field(None, description="LTREE path for hierarchy")
    depth: int = Field(0, description="Depth in hierarchy")
    parent_id: Optional[int] = Field(None, description="Parent entity ID")
    children_count: int = Field(0, description="Number of child entities")


# ============================================================================
# Profile Path Schemas
# ============================================================================

class ProfilePathCreate(BaseModel):
    """Schema for creating profile dependency paths."""
    
    company_id: int = Field(..., gt=0, description="Company entity ID")
    material_id: int = Field(..., gt=0, description="Material entity ID")
    opening_system_id: int = Field(..., gt=0, description="Opening system entity ID")
    system_series_id: int = Field(..., gt=0, description="System series entity ID")
    color_id: int = Field(..., gt=0, description="Color entity ID")


class ProfilePathDelete(BaseModel):
    """Schema for deleting profile dependency paths."""
    
    ltree_path: str = Field(..., min_length=1, description="LTREE path to delete")


class ProfilePathResponse(BaseModel):
    """Schema for profile path responses."""
    
    id: int = Field(..., description="Path node ID")
    ltree_path: str = Field(..., description="LTREE path")
    description: Optional[str] = Field(None, description="Path description")
    entities: Dict[str, ProfileEntityResponse] = Field(
        default_factory=dict, 
        description="Entities in this path"
    )
    total_price: Optional[Decimal] = Field(None, description="Total price for this path")
    created_at: str = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


# ============================================================================
# Profile Options Schemas
# ============================================================================

class ProfileDependentOptionsRequest(BaseModel):
    """Schema for requesting dependent options in profile hierarchy."""
    
    company_id: Optional[int] = Field(None, description="Selected company ID")
    material_id: Optional[int] = Field(None, description="Selected material ID")
    opening_system_id: Optional[int] = Field(None, description="Selected opening system ID")
    system_series_id: Optional[int] = Field(None, description="Selected system series ID")


class ProfileDependentOptionsResponse(BaseResponse):
    """Schema for dependent options response."""
    
    options: Dict[str, List[ProfileEntityResponse]] = Field(
        default_factory=dict,
        description="Available options by entity type"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about options"
    )


# ============================================================================
# Profile Scope Schemas
# ============================================================================

class ProfileHierarchyLevel(BaseModel):
    """Schema for profile hierarchy level definition."""
    
    level: int = Field(..., description="Hierarchy level (0-based)")
    entity_type: str = Field(..., description="Entity type at this level")
    label: str = Field(..., description="Display label")
    required: bool = Field(True, description="Whether selection is required")
    depends_on: Optional[str] = Field(None, description="Parent entity type")


class ProfileScopeResponse(BaseResponse):
    """Schema for profile scope configuration response."""
    
    scope: str = Field("profile", description="Scope name")
    label: str = Field("Profile System", description="Display label")
    hierarchy: List[ProfileHierarchyLevel] = Field(
        default_factory=list,
        description="Hierarchy level definitions"
    )
    entity_types: List[str] = Field(
        default_factory=lambda: ["company", "material", "opening_system", "system_series", "color"],
        description="Available entity types"
    )
    supports_paths: bool = Field(True, description="Whether scope supports dependency paths")
    supports_cascading: bool = Field(True, description="Whether scope supports cascading options")


# ============================================================================
# Profile Validation Schemas
# ============================================================================

class ProfilePathValidation(BaseModel):
    """Schema for validating profile paths."""
    
    path_data: ProfilePathCreate = Field(..., description="Path data to validate")
    check_duplicates: bool = Field(True, description="Check for duplicate paths")
    check_entities_exist: bool = Field(True, description="Check that all entities exist")


class ProfilePathValidationResponse(BaseResponse):
    """Schema for path validation response."""
    
    is_valid: bool = Field(..., description="Whether path is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggested_path: Optional[str] = Field(None, description="Suggested LTREE path")


# ============================================================================
# Profile Statistics Schemas
# ============================================================================

class ProfileEntityStats(BaseModel):
    """Schema for profile entity statistics."""
    
    entity_type: str = Field(..., description="Entity type")
    total_count: int = Field(..., description="Total number of entities")
    active_count: int = Field(..., description="Number of active entities")
    with_price_count: int = Field(..., description="Number of entities with pricing")
    avg_price: Optional[Decimal] = Field(None, description="Average price")


class ProfileScopeStats(BaseModel):
    """Schema for profile scope statistics."""
    
    total_entities: int = Field(..., description="Total entities across all types")
    total_paths: int = Field(..., description="Total dependency paths")
    entity_stats: List[ProfileEntityStats] = Field(
        default_factory=list,
        description="Statistics by entity type"
    )
    most_used_combinations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most frequently used entity combinations"
    )


# ============================================================================
# Profile Import/Export Schemas
# ============================================================================

class ProfileEntityImport(BaseModel):
    """Schema for importing profile entities."""
    
    entities: List[ProfileEntityCreate] = Field(..., description="Entities to import")
    update_existing: bool = Field(False, description="Whether to update existing entities")
    create_paths: bool = Field(False, description="Whether to create dependency paths")


class ProfileEntityExport(BaseModel):
    """Schema for exporting profile entities."""
    
    entity_types: Optional[List[str]] = Field(None, description="Entity types to export")
    include_paths: bool = Field(True, description="Whether to include dependency paths")
    include_metadata: bool = Field(True, description="Whether to include metadata")
    format: str = Field("json", pattern="^(json|csv|xlsx)$", description="Export format")


class ProfileImportResponse(BaseResponse):
    """Schema for import operation response."""
    
    imported_count: int = Field(..., description="Number of entities imported")
    updated_count: int = Field(..., description="Number of entities updated")
    skipped_count: int = Field(..., description="Number of entities skipped")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Import errors")