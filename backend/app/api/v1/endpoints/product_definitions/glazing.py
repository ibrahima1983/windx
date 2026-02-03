"""Glazing-specific product definition endpoints.

This module provides API endpoints for managing glazing product definitions
with compositional structure (glass types, spacers, gases, and glazing units).
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.types import CurrentSuperuser
from app.schemas.product_definition import (
    GlazingComponentCreate,
    GlazingUnitCreate,
    BaseResponse
)
from .base import BaseProductDefinitionEndpoints, EntityCreateRequest, EntityUpdateRequest

__all__ = ["GlazingProductDefinitionEndpoints"]


# ============================================================================
# Additional Glazing-Specific Schemas (not in main schema package yet)
# ============================================================================

from pydantic import BaseModel, Field

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
                data: GlazingUnitCreate,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Create a new glazing unit from components."""
            from app.services.product_definition import get_product_definition_service
            from app.services.product_definition.types import GlazingUnitData
            
            try:
                service = get_product_definition_service("glazing", db)
                
                # Convert request data to service data
                unit_data = GlazingUnitData(
                    name=data.name,
                    glazing_type=data.glazing_type,
                    description=data.description,
                    outer_glass_id=data.outer_glass_id,
                    middle_glass_id=data.middle_glass_id,
                    inner_glass_id=data.inner_glass_id,
                    spacer1_id=data.spacer1_id,
                    spacer2_id=data.spacer2_id,
                    gas_id=data.gas_id,
                )
                
                glazing_unit = await service.create_glazing_unit(unit_data)
                
                return {
                    "success": True,
                    "message": f"Glazing unit '{data.name}' created successfully",
                    "glazing_unit": glazing_unit
                }
            except Exception as e:
                print(f"[ERROR] Failed to create glazing unit: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create glazing unit. Please try again."
                )

        @self.router.get("/glazing-units")
        async def get_glazing_units(
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get all glazing units."""
            # TODO: Implement glazing unit storage and retrieval
            # For now, return empty list since glazing units are not yet stored in database
            return {
                "success": True,
                "glazing_units": [],
                "message": "Glazing units are created dynamically and not yet stored in database"
            }

        @self.router.post("/calculate")
        async def calculate_glazing_properties(
                data: GlazingCalculationRequest,
                db: AsyncSession = Depends(get_db),
        ) -> dict[str, Any]:
            """Calculate technical properties for a glazing unit configuration."""
            from app.services.product_definition import get_product_definition_service
            
            try:
                service = get_product_definition_service("glazing", db)
                
                # Convert request data to calculation format
                unit_data = {
                    "glazing_type": data.glazing_type,
                    **data.components
                }
                
                calculation_result = await service.calculate_glazing_properties(unit_data)
                
                return {
                    "success": True,
                    "calculated_properties": {
                        "total_thickness": calculation_result.total_thickness,
                        "u_value": calculation_result.u_value,
                        "price_per_sqm": float(calculation_result.price_per_sqm),
                        "weight_per_sqm": calculation_result.weight_per_sqm,
                        "technical_properties": calculation_result.technical_properties,
                    }
                }
            except Exception as e:
                print(f"[ERROR] Failed to calculate glazing properties: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to calculate glazing properties. Please try again."
                )

        @self.router.get("/components")
        async def get_all_components(
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get all glazing components grouped by type."""
            try:
                from app.services.product_definition import get_product_definition_service
                
                service = get_product_definition_service("glazing", db)
                components = await service.get_all_components()
                
                return {
                    "success": True,
                    "components": components
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
        """Create a glazing entity using the new service factory."""
        from app.services.product_definition import get_product_definition_service
        from app.services.product_definition.types import EntityCreateData
        
        # Prepare metadata for glazing components
        metadata = data.metadata or {}
        
        # If this is a GlazingComponentCreate, extract component-specific properties
        if isinstance(data, GlazingComponentCreate):
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
        
        service = get_product_definition_service("glazing", db)
        
        # Convert request data to service data
        entity_data = EntityCreateData(
            entity_type=data.entity_type,
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=metadata,
        )
        
        return await service.create_entity(entity_data)

    async def update_entity_impl(self, entity_id: int, data: EntityUpdateRequest, db: AsyncSession) -> Any:
        """Update a glazing entity using the new service factory."""
        from app.services.product_definition import get_product_definition_service
        from app.services.product_definition.types import EntityUpdateData
        
        service = get_product_definition_service("glazing", db)
        
        # Convert request data to service data
        update_data = EntityUpdateData(
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=data.metadata,
        )
        
        return await service.update_entity(entity_id, update_data)

    async def delete_entity_impl(self, entity_id: int, db: AsyncSession) -> dict[str, Any]:
        """Delete a glazing entity using the new service factory."""
        from app.services.product_definition import get_product_definition_service
        
        service = get_product_definition_service("glazing", db)
        return await service.delete_entity(entity_id)

    async def get_entities_by_type_impl(self, entity_type: str, db: AsyncSession) -> tuple[list[Any], dict[str, Any]]:
        """Get glazing entities by type using the new service factory."""
        from app.services.product_definition import get_product_definition_service
        
        service = get_product_definition_service("glazing", db)
        
        try:
            entities = await service.get_entities(entity_type)
            
            # Get type metadata from service
            scope_metadata = await service.get_scope_metadata()
            type_metadata = scope_metadata.get("entities", {}).get(entity_type, {})
            
            return entities, type_metadata
            
        except Exception as e:
            # If glazing scope is not configured, return empty results
            print(f"[WARNING] Glazing scope error for {entity_type}: {str(e)}")
            return [], {}