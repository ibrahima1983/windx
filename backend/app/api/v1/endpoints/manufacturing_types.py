"""Manufacturing Type management endpoints.

This module provides REST API endpoints for managing manufacturing types
(product categories like Window, Door, Table).

Public Variables:
    router: FastAPI router for manufacturing type endpoints

Features:
    - List manufacturing types with pagination and filters
    - Get manufacturing type by ID
    - Create new manufacturing type (superuser only)
    - Update manufacturing type (superuser only)
    - Delete/deactivate manufacturing type (superuser only)
    - OpenAPI documentation with examples
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import PositiveInt

from app.api.types import CurrentSuperuser, CurrentUser, DBSession
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.manufacturing_type import ManufacturingType
from app.schemas.manufacturing_type import (
    ManufacturingType as ManufacturingTypeSchema,
)
from app.schemas.manufacturing_type import ManufacturingTypeCreate, ManufacturingTypeUpdate
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    tags=["Manufacturing Types"],
    responses=get_common_responses(401, 500),
)


@router.get(
    "/",
    response_model=Page[ManufacturingTypeSchema],
    summary="List Manufacturing Types",
    description="List all manufacturing types with optional filtering by active status and category. Supports pagination and sorting.",
    response_description="Paginated list of manufacturing types",
    operation_id="listManufacturingTypes",
    responses={
        200: {
            "description": "Successfully retrieved manufacturing types",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "name": "Casement Window",
                                "description": "Energy-efficient casement windows",
                                "base_category": "window",
                                "image_url": "/images/casement.jpg",
                                "base_price": "200.00",
                                "base_weight": "15.00",
                                "is_active": True,
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z",
                            }
                        ],
                        "total": 10,
                        "page": 1,
                        "size": 50,
                        "pages": 1,
                    }
                }
            },
        },
        **get_common_responses(401, 500),
    },
)
async def list_manufacturing_types(
    current_user: CurrentUser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true=active, false=inactive, null=all)"),
    ] = None,
    base_category: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=50,
            description="Filter by base category (e.g., 'window', 'door', 'furniture')",
        ),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Search term for name or description (case-insensitive)",
        ),
    ] = None,
    sort_by: Annotated[
        Literal["created_at", "name", "base_price"],
        Query(description="Column to sort by"),
    ] = "created_at",
    sort_order: Annotated[
        Literal["asc", "desc"],
        Query(description="Sort direction (asc=ascending, desc=descending)"),
    ] = "desc",
) -> Page[ManufacturingType]:
    """List all manufacturing types with filtering and sorting.

    Provides comprehensive manufacturing type listing with optional filters for
    active status, category, and text search. Results can be sorted by creation
    date, name, or base price.

    Args:
        current_user (User): Current authenticated user
        params (PaginationParams): Pagination parameters (page, size)
        db (AsyncSession): Database session
        is_active (bool | None): Filter by active status (None = no filter)
        base_category (str | None): Filter by base category
        search (str | None): Search term for name or description
        sort_by (Literal): Column to sort by
        sort_order (Literal): Sort direction (asc, desc)

    Returns:
        Page[ManufacturingType]: Paginated list of manufacturing types

    Example:
        GET /api/v1/manufacturing-types?is_active=true&base_category=window&sort_by=name
    """
    from app.core.pagination import paginate
    from app.repositories.manufacturing_type import ManufacturingTypeRepository

    mfg_type_repo = ManufacturingTypeRepository(db)

    # Build filtered query
    query = mfg_type_repo.get_filtered(
        is_active=is_active,
        base_category=base_category,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Paginate the query
    return await paginate(db, query, params)


@router.get(
    "/{type_id}",
    response_model=ManufacturingTypeSchema,
    summary="Get Manufacturing Type",
    description="Get a single manufacturing type by ID",
    response_description="Manufacturing type details",
    operation_id="getManufacturingType",
    responses={
        200: {
            "description": "Successfully retrieved manufacturing type",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Casement Window",
                        "description": "Energy-efficient casement windows",
                        "base_category": "window",
                        "image_url": "/images/casement.jpg",
                        "base_price": "200.00",
                        "base_weight": "15.00",
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                }
            },
        },
        404: {
            "description": "Manufacturing type not found",
            "content": {
                "application/json": {"example": {"message": "Manufacturing type not found"}}
            },
        },
        **get_common_responses(401, 500),
    },
)
async def get_manufacturing_type(
    type_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> ManufacturingType:
    """Get manufacturing type by ID.

    Args:
        type_id (PositiveInt): Manufacturing type ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        ManufacturingType: Manufacturing type details

    Raises:
        NotFoundException: If manufacturing type not found

    Example:
        GET /api/v1/manufacturing-types/1
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.manufacturing_type import ManufacturingTypeRepository

    mfg_type_repo = ManufacturingTypeRepository(db)
    mfg_type = await mfg_type_repo.get(type_id)

    if not mfg_type:
        raise NotFoundException("Manufacturing type not found")

    return mfg_type


@router.post(
    "/",
    response_model=ManufacturingTypeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create Manufacturing Type",
    description="Create a new manufacturing type (superuser only)",
    response_description="Created manufacturing type",
    operation_id="createManufacturingType",
    responses={
        201: {
            "description": "Manufacturing type successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Casement Window",
                        "description": "Energy-efficient casement windows",
                        "base_category": "window",
                        "image_url": "/images/casement.jpg",
                        "base_price": "200.00",
                        "base_weight": "15.00",
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                }
            },
        },
        409: {
            "description": "Manufacturing type name already exists",
            "content": {
                "application/json": {
                    "example": {"message": "Manufacturing type with this name already exists"}
                }
            },
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def create_manufacturing_type(
    mfg_type_in: ManufacturingTypeCreate,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> ManufacturingType:
    """Create a new manufacturing type (superuser only).

    Args:
        mfg_type_in (ManufacturingTypeCreate): Manufacturing type creation data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        ManufacturingType: Created manufacturing type

    Raises:
        ConflictException: If name already exists
        AuthorizationException: If user is not superuser

    Example:
        POST /api/v1/manufacturing-types
        {
            "name": "Casement Window",
            "description": "Energy-efficient casement windows",
            "base_category": "window",
            "base_price": "200.00",
            "base_weight": "15.00"
        }
    """
    from app.core.exceptions import ConflictException
    from app.repositories.manufacturing_type import ManufacturingTypeRepository

    mfg_type_repo = ManufacturingTypeRepository(db)

    # Check if name already exists
    existing = await mfg_type_repo.get_by_name(mfg_type_in.name)
    if existing:
        raise ConflictException("Manufacturing type with this name already exists")

    # Create manufacturing type
    mfg_type = await mfg_type_repo.create(mfg_type_in)
    await db.commit()
    await db.refresh(mfg_type)

    return mfg_type


@router.patch(
    "/{type_id}",
    response_model=ManufacturingTypeSchema,
    summary="Update Manufacturing Type",
    description="Update an existing manufacturing type (superuser only)",
    response_description="Updated manufacturing type",
    operation_id="updateManufacturingType",
    responses={
        200: {
            "description": "Manufacturing type successfully updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Casement Window",
                        "description": "Updated description",
                        "base_category": "window",
                        "image_url": "/images/casement.jpg",
                        "base_price": "210.00",
                        "base_weight": "15.50",
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-15T00:00:00Z",
                    }
                }
            },
        },
        404: {
            "description": "Manufacturing type not found",
            "content": {
                "application/json": {"example": {"message": "Manufacturing type not found"}}
            },
        },
        409: {
            "description": "Manufacturing type name already exists",
            "content": {
                "application/json": {
                    "example": {"message": "Manufacturing type with this name already exists"}
                }
            },
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def update_manufacturing_type(
    type_id: PositiveInt,
    mfg_type_update: ManufacturingTypeUpdate,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> ManufacturingType:
    """Update manufacturing type (superuser only).

    Args:
        type_id (PositiveInt): Manufacturing type ID
        mfg_type_update (ManufacturingTypeUpdate): Update data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        ManufacturingType: Updated manufacturing type

    Raises:
        NotFoundException: If manufacturing type not found
        ConflictException: If name conflicts with existing type
        AuthorizationException: If user is not superuser

    Example:
        PATCH /api/v1/manufacturing-types/1
        {
            "description": "Updated description",
            "base_price": "210.00"
        }
    """
    from app.core.exceptions import ConflictException, NotFoundException
    from app.repositories.manufacturing_type import ManufacturingTypeRepository

    mfg_type_repo = ManufacturingTypeRepository(db)

    # Get existing manufacturing type
    mfg_type = await mfg_type_repo.get(type_id)
    if not mfg_type:
        raise NotFoundException("Manufacturing type not found")

    # Check name uniqueness if name is being updated
    if mfg_type_update.name and mfg_type_update.name != mfg_type.name:
        existing = await mfg_type_repo.get_by_name(mfg_type_update.name)
        if existing:
            raise ConflictException("Manufacturing type with this name already exists")

    # Update manufacturing type
    updated_mfg_type = await mfg_type_repo.update(mfg_type, mfg_type_update)
    await db.commit()
    await db.refresh(updated_mfg_type)

    return updated_mfg_type


@router.delete(
    "/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Manufacturing Type",
    description="Deactivate a manufacturing type (superuser only). This is a soft delete that sets is_active to false.",
    operation_id="deleteManufacturingType",
    responses={
        204: {
            "description": "Manufacturing type successfully deactivated",
        },
        404: {
            "description": "Manufacturing type not found",
            "content": {
                "application/json": {"example": {"message": "Manufacturing type not found"}}
            },
        },
        **get_common_responses(401, 403, 500),
    },
)
async def delete_manufacturing_type(
    type_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> None:
    """Delete (deactivate) manufacturing type (superuser only).

    This performs a soft delete by setting is_active to false.
    The manufacturing type remains in the database for historical records.

    Args:
        type_id (PositiveInt): Manufacturing type ID
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Raises:
        NotFoundException: If manufacturing type not found
        AuthorizationException: If user is not superuser

    Example:
        DELETE /api/v1/manufacturing-types/1
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.manufacturing_type import ManufacturingTypeRepository

    mfg_type_repo = ManufacturingTypeRepository(db)

    # Get existing manufacturing type
    mfg_type = await mfg_type_repo.get(type_id)
    if not mfg_type:
        raise NotFoundException("Manufacturing type not found")

    # Soft delete by deactivating
    mfg_type.is_active = False
    await db.commit()
