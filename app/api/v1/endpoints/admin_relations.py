"""Admin Relations API endpoints.

This module provides API endpoints for managing hierarchical option
dependencies (Company → Material → Opening System → System Series → Colors).

Public Variables:
    router: FastAPI router for relations endpoints
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.models.user import User
from app.services.relations import RelationsService

__all__ = ["router"]

router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory="app/templates")


# ============================================================================
# Pydantic Schemas
# ============================================================================

class EntityCreate(BaseModel):
    """Schema for creating a relation entity."""
    
    entity_type: str = Field(..., description="Type: company, material, opening_system, system_series, color, unit_type")
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
# HTML Page Endpoint
# ============================================================================

@router.get("/relations", response_class=HTMLResponse, name="admin_relations")
async def relations_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
):
    """Render the Relations management page.
    
    MVP: RBAC decorators commented out - page works without admin dashboard.
    """
    service = RelationsService(db)
    
    # Get all entities grouped by type
    entities = await service.get_all_entities()
    
    return templates.TemplateResponse(
        request,
        "admin/relations/index.html.jinja",
        {
            "active_page": "relations",
            "entities": entities,
        },
    )


# ============================================================================
# Entity CRUD Endpoints
# ============================================================================

@router.post("/relations/entities", status_code=status.HTTP_201_CREATED)
async def create_entity(
    data: EntityCreate,
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Create a new relation entity."""
    service = RelationsService(db)
    
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
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/relations/entities/{entity_id}")
async def update_entity(
    entity_id: int,
    data: EntityUpdate,
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Update an existing relation entity."""
    service = RelationsService(db)
    
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
        "message": f"Entity '{entity.name}' updated",
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "node_type": entity.node_type,
            "image_url": entity.image_url,
            "price_impact_value": str(entity.price_impact_value) if entity.price_impact_value else None,
            "description": entity.description,
            "validation_rules": entity.validation_rules,
        },
    }


@router.delete("/relations/entities/{entity_id}")
async def delete_entity(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Delete a relation entity."""
    service = RelationsService(db)
    result = await service.delete_entity(entity_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result


@router.get("/relations/entities/{entity_type}")
async def get_entities_by_type(
    entity_type: str,
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Get all entities of a specific type."""
    if entity_type not in RelationsService.ENTITY_METADATA:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")
    
    service = RelationsService(db)
    entities = await service.get_entities_by_type(entity_type)
    
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
            }
            for e in entities
        ],
    }


# ============================================================================
# Path Management Endpoints
# ============================================================================

@router.post("/relations/paths", status_code=status.HTTP_201_CREATED)
async def create_path(
    data: PathCreate,
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Create a new dependency path."""
    service = RelationsService(db)
    
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


@router.delete("/relations/paths")
async def delete_path(
    data: PathDelete,
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Delete a dependency path."""
    service = RelationsService(db)
    result = await service.delete_dependency_path(data.ltree_path)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result


@router.get("/relations/paths")
async def get_all_paths(
    db: AsyncSession = Depends(get_db),
    # TODO: Uncomment when RBAC is fully integrated
    # current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Get all dependency paths."""
    service = RelationsService(db)
    paths = await service.get_all_paths()
    
    return {
        "success": True,
        "paths": paths,
    }


# ============================================================================
# Cascading Options Endpoint
# ============================================================================

@router.post("/relations/options")
async def get_dependent_options(
    data: DependentOptionsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get dependent options based on parent selections.
    
    Used for cascading dropdowns in profile entry.
    """
    service = RelationsService(db)
    
    parent_selections = {
        "company": data.company_id,
        "material": data.material_id,
        "opening_system": data.opening_system_id,
        "system_series": data.system_series_id,
    }
    
    options = await service.get_dependent_options(parent_selections)
    
    return {
        "success": True,
        "options": options,
    }
