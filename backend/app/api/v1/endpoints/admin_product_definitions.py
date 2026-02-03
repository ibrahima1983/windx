"""Admin Product Definitions API endpoints.

⚠️  DEPRECATION WARNING: This module is deprecated and will be removed in a future version.
    Please use the new scope-based endpoints in app.api.v1.endpoints.product_definitions instead.

This module provides API endpoints for managing hierarchical option
dependencies (Company → Material → Opening System → System Series → Colors).

Public Variables:
    router: FastAPI router for relations endpoints
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.types import CurrentSuperuser
from app.services.product_definition import ProductDefinitionService

__all__ = ["router"]

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class EntityCreate(BaseModel):
    """Schema for creating a relation entity."""

    entity_type: str = Field(...,
                             description="Type: company, material, opening_system, system_series, color, unit_type")
    name: str = Field(..., min_length=1, max_length=200)
    image_url: str | None = Field(None, max_length=500)
    price_from: Decimal | None = Field(None, ge=0)
    description: str | None = Field(None)
    metadata: dict[str, Any] | None = Field(None, description="Extra metadata (density, u_value, etc.)")


class EntityUpdate(BaseModel):
    """Schema for updating a relation entity."""

    name: str | None = Field(None, min_length=1, max_length=200)
    image_url: str | None = Field(None, max_length=500)
    price_from: Decimal | None = Field(None, ge=0)
    description: str | None = Field(None)
    metadata: dict[str, Any] | None = Field(None)


class PathCreate(BaseModel):
    """Schema for creating a dependency path."""

    company_id: int = Field(..., gt=0)
    material_id: int = Field(..., gt=0)
    opening_system_id: int = Field(..., gt=0)
    system_series_id: int = Field(..., gt=0)
    color_id: int = Field(..., gt=0)


class PathDelete(BaseModel):
    """Schema for deleting a dependency path."""

    ltree_path: str = Field(..., min_length=1)


class DependentOptionsRequest(BaseModel):
    """Schema for requesting dependent options."""

    company_id: int | None = None
    material_id: int | None = None
    opening_system_id: int | None = None
    system_series_id: int | None = None


# ============================================================================
# Entity CRUD Endpoints
# ============================================================================

@router.post("/product-definitions/entities", status_code=status.HTTP_201_CREATED)
async def create_entity(
        data: EntityCreate,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Create a new relation entity."""
    service = ProductDefinitionService(db)

    try:
        entity = await service.create_entity(
            entity_type=data.entity_type,
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=data.metadata,
        )

        return {
            "success": True,
            "message": f"{data.entity_type.replace('_', ' ').title()} '{data.name}' created",
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "node_type": entity.node_type,
                "image_url": entity.image_url,
                "price_impact_value": str(entity.price_impact_value) if entity.price_impact_value else None,
                "description": entity.description,
                "validation_rules": entity.validation_rules,
                "metadata_": entity.metadata_,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle database errors and other unexpected errors
        error_msg = str(e)

        # Provide more specific error messages for common database issues
        if "duplicate key" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"An entity with the name '{data.name}' already exists. Please use a different name."
            )
        elif "foreign key" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Referenced item not found. Please check your selections and try again."
            )
        elif "invalid input" in error_msg.lower() or "cannot be interpreted" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Invalid data format provided. Please check your input values."
            )
        elif "not null" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Required field is missing. Please fill in all required information."
            )
        else:
            # Log the full error for debugging but return a user-friendly message
            print(f"[ERROR] Unexpected error creating entity: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create entity due to a server error. Please try again or contact support."
            )


@router.put("/product-definitions/entities/{entity_id}")
async def update_entity(
        entity_id: int,
        data: EntityUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Update an existing relation entity."""
    try:
        service = ProductDefinitionService(db)

        entity = await service.update_entity(
            entity_id=entity_id,
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=data.metadata,
        )

        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        return {
            "success": True,
            "message": f"Entity '{entity.name}' updated successfully",
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "node_type": entity.node_type,
                "image_url": entity.image_url,
                "price_impact_value": str(entity.price_impact_value) if entity.price_impact_value else None,
                "description": entity.description,
                "validation_rules": entity.validation_rules,
                "metadata_": entity.metadata_,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to update entity {entity_id}: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update entity: {error_msg}"
        )


@router.delete("/product-definitions/entities/{entity_id}")
async def delete_entity(
        entity_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Delete a relation entity."""
    service = ProductDefinitionService(db)
    result = await service.delete_entity(entity_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.get("/product-definitions/entities/{entity_type}")
async def get_entities_by_type(
        entity_type: str,
        scope: str | None = None,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Get all entities of a specific type."""
    try:
        service = ProductDefinitionService(db)
        entities = await service.get_entities_by_type(entity_type, scope=scope)

        # Get type metadata from database
        scopes = await service.get_definition_scopes()
        resolved_scope = await service.get_scope_for_entity(entity_type)
        type_metadata = scopes.get(resolved_scope, {}).get("entities", {}).get(entity_type, {})

        return {
            "success": True,
            "entities": [
                {
                    "id": e.id,
                    "name": e.name,
                    "node_type": e.node_type,
                    "image_url": e.image_url,
                    "price_impact_value": str(e.price_impact_value) if e.price_impact_value else None,
                    "description": e.description,
                    "validation_rules": e.validation_rules,
                    "metadata_": e.metadata_,
                }
                for e in entities
            ],
            "type_metadata": type_metadata,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to load entities for type '{entity_type}': {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load {entity_type.replace('_', ' ')} entities. Please try again."
        )


@router.get("/product-definitions/scopes")
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
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to load definition scopes: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load system configuration. Please contact support."
        )


# ============================================================================
# Path Management Endpoints
# ============================================================================

@router.post("/product-definitions/paths", status_code=status.HTTP_201_CREATED)
async def create_path(
        data: PathCreate,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Create a new dependency path."""
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


@router.delete("/product-definitions/paths")
async def delete_path(
        data: PathDelete,
        db: AsyncSession = Depends(get_db),
        current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Delete a dependency path."""
    service = ProductDefinitionService(db)
    result = await service.delete_dependency_path(data.ltree_path)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.get("/product-definitions/paths/{path_id}")
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


@router.get("/product-definitions/paths")
async def get_all_paths(
        db: AsyncSession = Depends(get_db),
        current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Get all dependency paths."""
    service = ProductDefinitionService(db)
    paths = await service.get_all_paths()

    return {
        "success": True,
        "paths": paths,
    }


# ============================================================================
# Cascading Options Endpoint
# ============================================================================

@router.post("/product-definitions/options")
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
