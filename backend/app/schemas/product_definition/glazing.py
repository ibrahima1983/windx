"""Glazing-specific schemas for product definitions.

This module provides schemas for the glazing scope which handles
compositional structure (glass types, spacers, gases, and glazing units).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from decimal import Decimal

from pydantic import BaseModel, Field

from .base import BaseEntityCreate, BaseEntityUpdate, BaseEntityResponse, BaseResponse

__all__ = [
    "GlazingComponentCreate",
    "GlazingComponentUpdate", 
    "GlazingComponentResponse",
    "GlazingUnitCreate",
    "GlazingUnitUpdate",
    "GlazingUnitResponse",
    "GlazingCalculationRequest",
    "GlazingCalculationResponse",
    "GlazingScopeResponse"
]


# ============================================================================
# Glazing Component Schemas
# ============================================================================

class GlazingComponentCreate(BaseEntityCreate):
    """Schema for creating glazing components."""
    
    # Override entity_type to be more specific for glazing
    entity_type: Literal["glass_type", "spacer", "gas"] = Field(
        ..., 
        description="Type of glazing component"
    )
    price_per_sqm: Optional[Decimal] = Field(
        None, 
        ge=0, 
        description="Price per square meter"
    )
    
    # Glass-specific properties
    thickness: Optional[float] = Field(
        None, 
        ge=0, 
        description="Thickness in mm (glass/spacer)"
    )
    light_transmittance: Optional[float] = Field(
        None, 
        ge=0, 
        le=100, 
        description="Light transmittance percentage (glass)"
    )
    u_value: Optional[float] = Field(
        None, 
        ge=0, 
        description="U-Value W/m²K (glass)"
    )
    
    # Spacer-specific properties
    material: Optional[str] = Field(
        None, 
        max_length=100, 
        description="Material type (spacer)"
    )
    thermal_conductivity: Optional[float] = Field(
        None, 
        ge=0, 
        description="Thermal conductivity W/m·K (spacer/gas)"
    )
    
    # Gas-specific properties
    density: Optional[float] = Field(
        None, 
        ge=0, 
        description="Density kg/m³ (gas)"
    )


class GlazingComponentUpdate(BaseEntityUpdate):
    """Schema for updating glazing components."""
    
    price_per_sqm: Optional[Decimal] = Field(
        None, 
        ge=0, 
        description="Price per square meter"
    )
    
    # Component-specific properties (same as create)
    thickness: Optional[float] = Field(None, ge=0, description="Thickness in mm")
    light_transmittance: Optional[float] = Field(None, ge=0, le=100, description="Light transmittance %")
    u_value: Optional[float] = Field(None, ge=0, description="U-Value W/m²K")
    material: Optional[str] = Field(None, max_length=100, description="Material type")
    thermal_conductivity: Optional[float] = Field(None, ge=0, description="Thermal conductivity W/m·K")
    density: Optional[float] = Field(None, ge=0, description="Density kg/m³")


class GlazingComponentResponse(BaseEntityResponse):
    """Schema for glazing component responses."""
    
    entity_type: str = Field(..., description="Type of glazing component")
    price_per_sqm: Optional[Decimal] = Field(None, description="Price per square meter")
    
    # Technical properties
    thickness: Optional[float] = Field(None, description="Thickness in mm")
    light_transmittance: Optional[float] = Field(None, description="Light transmittance %")
    u_value: Optional[float] = Field(None, description="U-Value W/m²K")
    material: Optional[str] = Field(None, description="Material type")
    thermal_conductivity: Optional[float] = Field(None, description="Thermal conductivity W/m·K")
    density: Optional[float] = Field(None, description="Density kg/m³")
    
    # Usage statistics
    usage_count: int = Field(0, description="Number of times used in glazing units")
    is_active: bool = Field(True, description="Whether component is active")


# ============================================================================
# Glazing Unit Schemas
# ============================================================================

class GlazingUnitCreate(BaseModel):
    """Schema for creating glazing units."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Glazing unit name")
    glazing_type: Literal["single", "double", "triple"] = Field(
        ..., 
        description="Type of glazing unit"
    )
    description: Optional[str] = Field(None, description="Unit description")
    
    # Component references
    outer_glass_id: Optional[int] = Field(
        None, 
        description="Outer glass component ID"
    )
    middle_glass_id: Optional[int] = Field(
        None, 
        description="Middle glass component ID (triple only)"
    )
    inner_glass_id: Optional[int] = Field(
        None, 
        description="Inner glass component ID (double/triple)"
    )
    spacer1_id: Optional[int] = Field(
        None, 
        description="First spacer ID (double/triple)"
    )
    spacer2_id: Optional[int] = Field(
        None, 
        description="Second spacer ID (triple only)"
    )
    gas_id: Optional[int] = Field(
        None, 
        description="Gas filling ID (optional)"
    )


class GlazingUnitUpdate(BaseModel):
    """Schema for updating glazing units."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Glazing unit name")
    description: Optional[str] = Field(None, description="Unit description")
    
    # Component references (same as create)
    outer_glass_id: Optional[int] = Field(None, description="Outer glass component ID")
    middle_glass_id: Optional[int] = Field(None, description="Middle glass component ID")
    inner_glass_id: Optional[int] = Field(None, description="Inner glass component ID")
    spacer1_id: Optional[int] = Field(None, description="First spacer ID")
    spacer2_id: Optional[int] = Field(None, description="Second spacer ID")
    gas_id: Optional[int] = Field(None, description="Gas filling ID")


class GlazingUnitResponse(BaseEntityResponse):
    """Schema for glazing unit responses."""
    
    glazing_type: str = Field(..., description="Type of glazing unit")
    
    # Component information
    components: Dict[str, Optional[GlazingComponentResponse]] = Field(
        default_factory=dict,
        description="Components used in this unit"
    )
    
    # Calculated properties
    total_thickness: float = Field(..., description="Total thickness in mm")
    u_value: float = Field(..., description="Calculated U-Value W/m²K")
    price_per_sqm: Decimal = Field(..., description="Calculated price per square meter")
    weight_per_sqm: float = Field(..., description="Calculated weight per square meter")
    
    # Technical properties
    technical_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional technical properties"
    )
    
    # Status
    is_valid: bool = Field(True, description="Whether unit configuration is valid")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")


# ============================================================================
# Glazing Calculation Schemas
# ============================================================================

class GlazingCalculationRequest(BaseModel):
    """Schema for calculating glazing unit properties."""
    
    glazing_type: Literal["single", "double", "triple"] = Field(
        ..., 
        description="Type of glazing unit"
    )
    components: Dict[str, Optional[int]] = Field(
        ..., 
        description="Component IDs by role"
    )
    custom_properties: Optional[Dict[str, Any]] = Field(
        None, 
        description="Custom properties to override"
    )


class GlazingCalculationResponse(BaseResponse):
    """Schema for glazing calculation results."""
    
    calculated_properties: Dict[str, Any] = Field(
        ...,
        description="Calculated properties"
    )
    breakdown: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed calculation breakdown"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Calculation warnings"
    )


# ============================================================================
# Glazing Scope Schemas
# ============================================================================

class GlazingComponentTypeConfig(BaseModel):
    """Configuration for a glazing component type."""
    
    component_type: str = Field(..., description="Component type")
    label: str = Field(..., description="Display label")
    icon: Optional[str] = Field(None, description="Icon class")
    required_properties: List[str] = Field(
        default_factory=list,
        description="Required properties for this component type"
    )
    optional_properties: List[str] = Field(
        default_factory=list,
        description="Optional properties for this component type"
    )


class GlazingScopeResponse(BaseResponse):
    """Schema for glazing scope configuration response."""
    
    scope: str = Field("glazing", description="Scope name")
    label: str = Field("Glazing System", description="Display label")
    component_types: List[GlazingComponentTypeConfig] = Field(
        default_factory=list,
        description="Available component types"
    )
    glazing_types: List[str] = Field(
        default_factory=lambda: ["single", "double", "triple"],
        description="Available glazing unit types"
    )
    supports_calculations: bool = Field(True, description="Whether scope supports calculations")
    supports_composition: bool = Field(True, description="Whether scope supports composition")


# ============================================================================
# Glazing Statistics Schemas
# ============================================================================

class GlazingComponentStats(BaseModel):
    """Schema for glazing component statistics."""
    
    component_type: str = Field(..., description="Component type")
    total_count: int = Field(..., description="Total number of components")
    active_count: int = Field(..., description="Number of active components")
    avg_price: Optional[Decimal] = Field(None, description="Average price per sqm")
    price_range: Optional[Dict[str, Decimal]] = Field(None, description="Price range (min/max)")


class GlazingUnitStats(BaseModel):
    """Schema for glazing unit statistics."""
    
    glazing_type: str = Field(..., description="Glazing unit type")
    total_count: int = Field(..., description="Total number of units")
    avg_thickness: Optional[float] = Field(None, description="Average thickness")
    avg_u_value: Optional[float] = Field(None, description="Average U-value")
    avg_price: Optional[Decimal] = Field(None, description="Average price per sqm")


class GlazingScopeStats(BaseModel):
    """Schema for glazing scope statistics."""
    
    total_components: int = Field(..., description="Total components across all types")
    total_units: int = Field(..., description="Total glazing units")
    component_stats: List[GlazingComponentStats] = Field(
        default_factory=list,
        description="Statistics by component type"
    )
    unit_stats: List[GlazingUnitStats] = Field(
        default_factory=list,
        description="Statistics by unit type"
    )
    popular_combinations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most popular component combinations"
    )


# ============================================================================
# Glazing Import/Export Schemas
# ============================================================================

class GlazingComponentImport(BaseModel):
    """Schema for importing glazing components."""
    
    components: List[GlazingComponentCreate] = Field(..., description="Components to import")
    update_existing: bool = Field(False, description="Whether to update existing components")
    validate_properties: bool = Field(True, description="Whether to validate component properties")


class GlazingUnitImport(BaseModel):
    """Schema for importing glazing units."""
    
    units: List[GlazingUnitCreate] = Field(..., description="Units to import")
    update_existing: bool = Field(False, description="Whether to update existing units")
    recalculate_properties: bool = Field(True, description="Whether to recalculate properties")


class GlazingExport(BaseModel):
    """Schema for exporting glazing data."""
    
    include_components: bool = Field(True, description="Whether to include components")
    include_units: bool = Field(True, description="Whether to include units")
    component_types: Optional[List[str]] = Field(None, description="Component types to export")
    unit_types: Optional[List[str]] = Field(None, description="Unit types to export")
    include_calculations: bool = Field(True, description="Whether to include calculated properties")
    format: str = Field("json", pattern="^(json|csv|xlsx)$", description="Export format")


class GlazingImportResponse(BaseResponse):
    """Schema for glazing import operation response."""
    
    components_imported: int = Field(0, description="Number of components imported")
    components_updated: int = Field(0, description="Number of components updated")
    units_imported: int = Field(0, description="Number of units imported")
    units_updated: int = Field(0, description="Number of units updated")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Import errors")
    warnings: List[str] = Field(default_factory=list, description="Import warnings")