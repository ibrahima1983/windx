"""Glazing-specific product definition endpoints.

This module provides API endpoints for managing glazing product definitions
with compositional structure (glass types, spacers, gases, and glazing units).
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.types import CurrentSuperuser
from .base import BaseProductDefinitionEndpoints, EntityCreateRequest, EntityUpdateRequest

__all__ = ["GlazingProductDefinitionEndpoints"]


# ============================================================================
# Glazing-Specific Schemas
# ============================================================================

class GlazingComponentCreateRequest(EntityCreateRequest):
    """Schema for creating glazing components (glass_type, spacer, gas)."""
    
    # Override entity_type to be more specific for glazing
    entity_type: Literal["glass_type", "spacer", "gas"] = Field(..., description="Type of glazing component")
    
    # Component-specific properties (stored in metadata)
    thickness: float | None = Field(None, description="Thickness in mm (glass/spacer)")
    light_transmittance: float | None = Field(None, description="Light transmittance % (glass)")
    u_value: float | None = Field(None, description="U-Value W/m²K (glass)")
    material: str | None = Field(None, description="Material type (spacer)")
    thermal_conductivity: float | None = Field(None, description="Thermal conductivity (spacer/gas)")
    density: float | None = Field(None, description="Density kg/m³ (gas)")


class GlazingUnitCreateRequest(BaseModel):
    """Schema for creating glazing units (single/double/triple)."""
    
    name: str = Field(..., min_length=1, max_length=200)
    glazing_type: Literal["single", "double", "triple"]
    description: str | None = None
    
    # Component references
    outer_glass_id: int | None = Field(None, description="Outer glass component ID")
    middle_glass_id: int | None = Field(None, description="Middle glass component ID (triple only)")
    inner_glass_id: int | None = Field(None, description="Inner glass component ID (double/triple)")
    spacer1_id: int | None = Field(None, description="First spacer ID (double/triple)")
    spacer2_id: int | None = Field(None, description="Second spacer ID (triple only)")
    gas_id: int | None = Field(None, description="Gas filling ID (optional)")


class GlazingCalculationRequest(BaseModel):
    """Schema for calculating glazing unit properties."""
    
    glazing_type: Literal["single", "double", "triple"]
    components: dict[str, int] = Field(..., description="Component IDs by role")


# ============================================================================
# Glazing Endpoints Implementation
# ============================================================================

class GlazingProductDefinitionEndpoints(BaseProductDefinitionEndpoints):
    """Glazing-specific product definition endpoints.
    
    Handles compositional structure for glazing system:
    - Components: glass_type, spacer, gas
    - Glazing Units: single, double, triple compositions
    """

    def __init__(self):
        """Initialize glazing endpoints."""
        super().__init__("glazing")

    def _setup_scope_routes(self) -> None:
        """Setup glazing-specific routes."""
        
        @self.router.post("/glazing-units")
        async def create_glazing_unit(
                data: GlazingUnitCreateRequest,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Create a new glazing unit from components."""
            # TODO: Implement glazing unit creation logic
            # This is a placeholder for Phase 2 implementation
            return {
                "success": True,
                "message": f"Glazing unit '{data.name}' creation not yet implemented",
                "glazing_unit": {
                    "name": data.name,
                    "glazing_type": data.glazing_type,
                    "description": data.description,
                    "components": {
                        "outer_glass_id": data.outer_glass_id,
                        "middle_glass_id": data.middle_glass_id,
                        "inner_glass_id": data.inner_glass_id,
                        "spacer1_id": data.spacer1_id,
                        "spacer2_id": data.spacer2_id,
                        "gas_id": data.gas_id,
                    }
                }
            }

        @self.router.get("/glazing-units")
        async def get_glazing_units(
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get all glazing units."""
            # TODO: Implement glazing unit retrieval logic
            # This is a placeholder for Phase 2 implementation
            return {
                "success": True,
                "glazing_units": [],
                "message": "Glazing unit retrieval not yet implemented"
            }

        @self.router.post("/calculate")
        async def calculate_glazing_properties(
                data: GlazingCalculationRequest,
                db: AsyncSession = Depends(get_db),
        ) -> dict[str, Any]:
            """Calculate technical properties for a glazing unit configuration."""
            # TODO: Implement glazing calculation logic
            # This is a placeholder for Phase 2 implementation
            return {
                "success": True,
                "calculated_properties": {
                    "total_thickness": 0.0,
                    "u_value": 0.0,
                    "price_per_sqm": 0.0,
                    "weight_per_sqm": 0.0,
                },
                "message": "Glazing calculation not yet implemented"
            }

        @self.router.get("/components")
        async def get_all_components(
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get all glazing components grouped by type."""
            try:
                # Get components by type
                glass_types = await self.get_entities_by_type_impl("glass_type", db)
                spacers = await self.get_entities_by_type_impl("spacer", db)
                gases = await self.get_entities_by_type_impl("gas", db)
                
                return {
                    "success": True,
                    "components": {
                        "glass_types": [
                            {
                                "id": e.id,
                                "name": e.name,
                                "description": e.description,
                                "image_url": e.image_url,
                                "metadata_": e.metadata_,
                            }
                            for e in glass_types[0]
                        ],
                        "spacers": [
                            {
                                "id": e.id,
                                "name": e.name,
                                "description": e.description,
                                "image_url": e.image_url,
                                "metadata_": e.metadata_,
                            }
                            for e in spacers[0]
                        ],
                        "gases": [
                            {
                                "id": e.id,
                                "name": e.name,
                                "description": e.description,
                                "image_url": e.image_url,
                                "metadata_": e.metadata_,
                            }
                            for e in gases[0]
                        ],
                    }
                }
            except Exception as e:
                print(f"[ERROR] Failed to load glazing components: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to load glazing components. Please try again."
                )

    # ============================================================================
    # Base Class Implementation
    # ============================================================================

    async def create_entity_impl(self, data: EntityCreateRequest, db: AsyncSession) -> Any:
        """Create a glazing entity.
        
        For now, this delegates to the existing ProductDefinitionService
        but stores glazing-specific metadata.
        """
        # Import here to avoid circular imports
        from app.services.product_definition import ProductDefinitionService
        
        # Prepare metadata for glazing components
        metadata = data.metadata or {}
        
        # If this is a GlazingComponentCreateRequest, extract component-specific properties
        if isinstance(data, GlazingComponentCreateRequest):
            if data.thickness is not None:
                metadata["thickness"] = data.thickness
            if data.light_transmittance is not None:
                metadata["light_transmittance"] = data.light_transmittance
            if data.u_value is not None:
                metadata["u_value"] = data.u_value
            if data.material is not None:
                metadata["material"] = data.material
            if data.thermal_conductivity is not None:
                metadata["thermal_conductivity"] = data.thermal_conductivity
            if data.density is not None:
                metadata["density"] = data.density
        
        service = ProductDefinitionService(db)
        return await service.create_entity(
            entity_type=data.entity_type,
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=metadata,
        )

    async def update_entity_impl(self, entity_id: int, data: EntityUpdateRequest, db: AsyncSession) -> Any:
        """Update a glazing entity using the existing service."""
        from app.services.product_definition import ProductDefinitionService
        
        service = ProductDefinitionService(db)
        return await service.update_entity(
            entity_id=entity_id,
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=data.metadata,
        )

    async def delete_entity_impl(self, entity_id: int, db: AsyncSession) -> dict[str, Any]:
        """Delete a glazing entity using the existing service."""
        from app.services.product_definition import ProductDefinitionService
        
        service = ProductDefinitionService(db)
        return await service.delete_entity(entity_id)

    async def get_entities_by_type_impl(self, entity_type: str, db: AsyncSession) -> tuple[list[Any], dict[str, Any]]:
        """Get glazing entities by type.
        
        For now, this uses the existing service but filters by glazing scope.
        """
        from app.services.product_definition import ProductDefinitionService
        
        service = ProductDefinitionService(db)
        
        try:
            entities = await service.get_entities_by_type(entity_type, scope="glazing")
            
            # Get type metadata - for now return empty metadata since glazing scope may not be fully configured
            type_metadata = {
                "label": entity_type.replace('_', ' ').title(),
                "icon": "pi pi-box",
                "help_text": f"Manage {entity_type} for glazing system"
            }
            
            return entities, type_metadata
            
        except Exception as e:
            # If glazing scope is not configured, return empty results
            print(f"[WARNING] Glazing scope not configured for {entity_type}: {str(e)}")
            return [], {}