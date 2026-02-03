"""Profile-specific product definition endpoints.

This module provides API endpoints for managing profile product definitions
with hierarchical dependencies (Company → Material → Opening System → System Series → Colors).
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.types import CurrentSuperuser
from app.services.product_definition import ProductDefinitionService
from .base import BaseProductDefinitionEndpoints, EntityCreateRequest, EntityUpdateRequest

__all__ = ["ProfileProductDefinitionEndpoints"]


# ============================================================================
# Profile-Specific Schemas
# ============================================================================

class PathCreateRequest(BaseModel):
    """Schema for creating a profile dependency path."""

    company_id: int = Field(..., gt=0)
    material_id: int = Field(..., gt=0)
    opening_system_id: int = Field(..., gt=0)
    system_series_id: int = Field(..., gt=0)
    color_id: int = Field(..., gt=0)


class PathDeleteRequest(BaseModel):
    """Schema for deleting a profile dependency path."""

    ltree_path: str = Field(..., min_length=1)


class DependentOptionsRequest(BaseModel):
    """Schema for requesting dependent options in profile hierarchy."""

    company_id: int | None = None
    material_id: int | None = None
    opening_system_id: int | None = None
    system_series_id: int | None = None


# ============================================================================
# Profile Endpoints Implementation
# ============================================================================

class ProfileProductDefinitionEndpoints(BaseProductDefinitionEndpoints):
    """Profile-specific product definition endpoints.
    
    Handles hierarchical dependencies for profile system:
    Company → Material → Opening System → System Series → Color
    """

    def __init__(self):
        """Initialize profile endpoints."""
        super().__init__("profile")

    def _setup_scope_routes(self) -> None:
        """Setup profile-specific routes."""
        
        @self.router.post("/paths")
        async def create_path(
                data: PathCreateRequest,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Create a new profile dependency path."""
            service = ProductDefinitionService(db)

            try:
                path_node = await service.create_dependency_path(
                    company_id=data.company_id,
                    material_id=data.material_id,
                    opening_system_id=data.opening_system_id,
                    system_series_id=data.system_series_id,
                    color_id=data.color_id,
                )

                return {
                    "success": True,
                    "message": "Dependency path created",
                    "path": {
                        "id": path_node.id,
                        "ltree_path": path_node.ltree_path,
                        "description": path_node.description,
                    },
                }
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.delete("/paths")
        async def delete_path(
                data: PathDeleteRequest,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Delete a profile dependency path."""
            service = ProductDefinitionService(db)
            result = await service.delete_dependency_path(data.ltree_path)

            if not result["success"]:
                raise HTTPException(status_code=404, detail=result["message"])

            return result

        @self.router.get("/paths/{path_id}")
        async def get_path_details(
                path_id: int,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get detailed path information with all related entities."""
            try:
                service = ProductDefinitionService(db)
                path_details = await service.get_path_details(path_id)

                if not path_details:
                    raise HTTPException(status_code=404, detail="Path not found")

                return {
                    "success": True,
                    "path": path_details
                }
            except HTTPException:
                raise
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Failed to load path details for ID '{path_id}': {error_msg}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to load path details. Please try again."
                )

        @self.router.get("/paths")
        async def get_all_paths(
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get all profile dependency paths."""
            service = ProductDefinitionService(db)
            paths = await service.get_all_paths()

            return {
                "success": True,
                "paths": paths,
            }

        @self.router.post("/options")
        async def get_dependent_options(
                data: DependentOptionsRequest,
                db: AsyncSession = Depends(get_db),
        ) -> dict[str, Any]:
            """Get dependent options based on parent selections.
            
            Used for cascading dropdowns in profile entry.
            Note: This endpoint doesn't require authentication as it's used by the public profile entry.
            """
            service = ProductDefinitionService(db)

            parent_selections = {
                "company_id": data.company_id,
                "material_id": data.material_id,
                "opening_system_id": data.opening_system_id,
                "system_series_id": data.system_series_id,
            }

            options = await service.get_dependent_options(parent_selections)

            return {
                "success": True,
                "options": options,
            }

        @self.router.get("/scopes")
        async def get_definition_scopes(
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get available definition scopes with full schema details."""
            try:
                service = ProductDefinitionService(db)
                scopes = await service.get_definition_scopes()

                if not scopes:
                    raise HTTPException(
                        status_code=500,
                        detail="No product definition scopes found. Please run the setup script to initialize the system."
                    )

                return {
                    "success": True,
                    "scopes": scopes
                }
            except HTTPException:
                raise
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Failed to load definition scopes: {error_msg}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to load system configuration. Please contact support."
                )

    # ============================================================================
    # Base Class Implementation
    # ============================================================================

    async def create_entity_impl(self, data: EntityCreateRequest, db: AsyncSession) -> Any:
        """Create a profile entity using the existing service."""
        service = ProductDefinitionService(db)
        return await service.create_entity(
            entity_type=data.entity_type,
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=data.metadata,
        )

    async def update_entity_impl(self, entity_id: int, data: EntityUpdateRequest, db: AsyncSession) -> Any:
        """Update a profile entity using the existing service."""
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
        """Delete a profile entity using the existing service."""
        service = ProductDefinitionService(db)
        return await service.delete_entity(entity_id)

    async def get_entities_by_type_impl(self, entity_type: str, db: AsyncSession) -> tuple[list[Any], dict[str, Any]]:
        """Get profile entities by type using the existing service."""
        service = ProductDefinitionService(db)
        entities = await service.get_entities_by_type(entity_type, scope="profile")
        
        # Get type metadata from database
        scopes = await service.get_definition_scopes()
        resolved_scope = await service.get_scope_for_entity(entity_type)
        type_metadata = scopes.get(resolved_scope, {}).get("entities", {}).get(entity_type, {})
        
        return entities, type_metadata