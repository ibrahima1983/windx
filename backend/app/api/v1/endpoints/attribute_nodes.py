"""Attribute Node management endpoints.

This module provides REST API endpoints for managing attribute nodes
in the hierarchical product configuration system.

Public Variables:
    router: FastAPI router for attribute node endpoints

Features:
    - List attribute nodes with filters
    - Get attribute node by ID
    - Get direct children of a node
    - Get full subtree of descendants
    - Create new attribute node (superuser only)
    - Update attribute node (superuser only)
    - Delete attribute node (superuser only)
    - OpenAPI documentation with examples
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import PositiveInt

from app.api.types import CurrentSuperuser, CurrentUser, DBSession
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.attribute_node import AttributeNode
from app.schemas.attribute_node import (
    AttributeNode as AttributeNodeSchema,
)
from app.schemas.attribute_node import (
    AttributeNodeCreate,
    AttributeNodeTree,
    AttributeNodeUpdate,
)
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    tags=["Attribute Nodes"],
    responses=get_common_responses(401, 500),
)


@router.get(
    "/",
    response_model=Page[AttributeNodeSchema],
    summary="List Attribute Nodes",
    description="List attribute nodes with optional filtering by manufacturing type",
    response_description="Paginated list of attribute nodes",
    operation_id="listAttributeNodes",
    responses={
        200: {
            "description": "Successfully retrieved attribute nodes",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "manufacturing_type_id": 1,
                                "parent_node_id": None,
                                "name": "Frame Options",
                                "node_type": "category",
                                "data_type": None,
                                "ltree_path": "frame_options",
                                "depth": 0,
                                "sort_order": 1,
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z",
                            }
                        ],
                        "total": 50,
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
async def list_attribute_nodes(
    current_user: CurrentUser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    manufacturing_type_id: Annotated[
        PositiveInt | None,
        Query(description="Filter by manufacturing type ID"),
    ] = None,
    parent_node_id: Annotated[
        int | None,
        Query(description="Filter by parent node ID (null for root nodes)"),
    ] = None,
    node_type: Annotated[
        str | None,
        Query(description="Filter by node type (category, attribute, option, etc.)"),
    ] = None,
) -> Page[AttributeNode]:
    """List attribute nodes with filtering.

    Args:
        current_user (User): Current authenticated user
        params (PaginationParams): Pagination parameters
        db (AsyncSession): Database session
        manufacturing_type_id (PositiveInt | None): Filter by manufacturing type
        parent_node_id (int | None): Filter by parent node
        node_type (str | None): Filter by node type

    Returns:
        Page[AttributeNode]: Paginated list of attribute nodes

    Example:
        GET /api/v1/attribute-nodes?manufacturing_type_id=1&node_type=option
    """
    from app.core.pagination import paginate
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_node_repo = AttributeNodeRepository(db)

    # Build filtered query
    query = attr_node_repo.get_filtered(
        manufacturing_type_id=manufacturing_type_id,
        parent_node_id=parent_node_id,
        node_type=node_type,
    )

    return await paginate(db, query, params)


@router.get(
    "/{node_id}",
    response_model=AttributeNodeSchema,
    summary="Get Attribute Node",
    description="Get a single attribute node by ID",
    response_description="Attribute node details",
    operation_id="getAttributeNode",
    responses={
        200: {
            "description": "Successfully retrieved attribute node",
        },
        404: {
            "description": "Attribute node not found",
            "content": {"application/json": {"example": {"message": "Attribute node not found"}}},
        },
        **get_common_responses(401, 500),
    },
)
async def get_attribute_node(
    node_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> AttributeNode:
    """Get attribute node by ID.

    Args:
        node_id (PositiveInt): Attribute node ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        AttributeNode: Attribute node details

    Raises:
        NotFoundException: If attribute node not found
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_node_repo = AttributeNodeRepository(db)
    node = await attr_node_repo.get(node_id)

    if not node:
        raise NotFoundException("Attribute node not found")

    return node


@router.get(
    "/{node_id}/children",
    response_model=list[AttributeNodeSchema],
    summary="Get Child Nodes",
    description="Get direct children of an attribute node",
    response_description="List of child nodes",
    operation_id="getAttributeNodeChildren",
    responses={
        200: {
            "description": "Successfully retrieved child nodes",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 2,
                            "manufacturing_type_id": 1,
                            "parent_node_id": 1,
                            "name": "Material Type",
                            "node_type": "attribute",
                            "data_type": "string",
                            "ltree_path": "frame_options.material_type",
                            "depth": 1,
                            "sort_order": 1,
                        }
                    ]
                }
            },
        },
        404: {
            "description": "Attribute node not found",
        },
        **get_common_responses(401, 500),
    },
)
async def get_attribute_node_children(
    node_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> list[AttributeNode]:
    """Get direct children of an attribute node.

    Args:
        node_id (PositiveInt): Parent node ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        list[AttributeNode]: List of child nodes

    Raises:
        NotFoundException: If parent node not found
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_node_repo = AttributeNodeRepository(db)

    # Verify parent exists
    parent = await attr_node_repo.get(node_id)
    if not parent:
        raise NotFoundException("Attribute node not found")

    # Get children
    children = await attr_node_repo.get_children(node_id)
    return children


@router.get(
    "/{node_id}/tree",
    response_model=list[AttributeNodeTree],
    summary="Get Node Subtree",
    description="Get full subtree of descendants for an attribute node using LTREE",
    response_description="Hierarchical tree structure",
    operation_id="getAttributeNodeTree",
    responses={
        200: {
            "description": "Successfully retrieved node subtree",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "Frame Options",
                            "node_type": "category",
                            "children": [
                                {
                                    "id": 2,
                                    "name": "Material Type",
                                    "node_type": "attribute",
                                    "children": [
                                        {
                                            "id": 3,
                                            "name": "Aluminum",
                                            "node_type": "option",
                                            "children": [],
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            },
        },
        404: {
            "description": "Attribute node not found",
        },
        **get_common_responses(401, 500),
    },
)
async def get_attribute_node_tree(
    node_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> list[AttributeNodeTree]:
    """Get full subtree of descendants using LTREE.

    Returns a hierarchical tree structure with all descendants
    organized by parent-child relationships.

    Args:
        node_id (PositiveInt): Root node ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        list[AttributeNodeTree]: Hierarchical tree structure

    Raises:
        NotFoundException: If node not found
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_node_repo = AttributeNodeRepository(db)

    # Verify node exists
    node = await attr_node_repo.get(node_id)
    if not node:
        raise NotFoundException("Attribute node not found")

    # Get all descendants using LTREE
    descendants = await attr_node_repo.get_descendants(node_id)

    # Build tree structure
    tree = attr_node_repo.build_tree([node] + descendants)
    return tree


@router.post(
    "/",
    response_model=AttributeNodeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create Attribute Node",
    description="Create a new attribute node (superuser only)",
    response_description="Created attribute node",
    operation_id="createAttributeNode",
    responses={
        201: {
            "description": "Attribute node successfully created",
        },
        404: {
            "description": "Parent node or manufacturing type not found",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def create_attribute_node(
    node_in: AttributeNodeCreate,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> AttributeNode:
    """Create a new attribute node (superuser only).

    The LTREE path and depth are automatically calculated based on
    the parent node.

    Args:
        node_in (AttributeNodeCreate): Attribute node creation data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        AttributeNode: Created attribute node

    Raises:
        NotFoundException: If parent or manufacturing type not found
        AuthorizationException: If user is not superuser

    Example:
        POST /api/v1/attribute-nodes
        {
            "manufacturing_type_id": 1,
            "parent_node_id": 1,
            "name": "Material Type",
            "node_type": "attribute",
            "data_type": "string",
            "required": true
        }
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.attribute_node import AttributeNodeRepository
    from app.repositories.manufacturing_type import ManufacturingTypeRepository

    attr_node_repo = AttributeNodeRepository(db)
    mfg_type_repo = ManufacturingTypeRepository(db)

    # Verify manufacturing type exists
    if node_in.manufacturing_type_id:
        mfg_type = await mfg_type_repo.get(node_in.manufacturing_type_id)
        if not mfg_type:
            raise NotFoundException("Manufacturing type not found")

    # Verify parent exists if specified
    if node_in.parent_node_id:
        parent = await attr_node_repo.get(node_in.parent_node_id)
        if not parent:
            raise NotFoundException("Parent node not found")

    # Create attribute node (LTREE path calculated automatically)
    node = await attr_node_repo.create(node_in)
    await db.commit()
    await db.refresh(node)

    return node


@router.patch(
    "/{node_id}",
    response_model=AttributeNodeSchema,
    summary="Update Attribute Node",
    description="Update an existing attribute node (superuser only)",
    response_description="Updated attribute node",
    operation_id="updateAttributeNode",
    responses={
        200: {
            "description": "Attribute node successfully updated",
        },
        404: {
            "description": "Attribute node not found",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def update_attribute_node(
    node_id: PositiveInt,
    node_update: AttributeNodeUpdate,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> AttributeNode:
    """Update attribute node (superuser only).

    If parent_node_id is changed, the LTREE path and depth are
    automatically recalculated for this node and all descendants.

    Args:
        node_id (PositiveInt): Attribute node ID
        node_update (AttributeNodeUpdate): Update data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        AttributeNode: Updated attribute node

    Raises:
        NotFoundException: If node not found
        AuthorizationException: If user is not superuser

    Example:
        PATCH /api/v1/attribute-nodes/1
        {
            "name": "Updated Name",
            "description": "Updated description"
        }
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_node_repo = AttributeNodeRepository(db)

    # Get existing node
    node = await attr_node_repo.get(node_id)
    if not node:
        raise NotFoundException("Attribute node not found")

    # Update node
    updated_node = await attr_node_repo.update(node, node_update)
    await db.commit()
    await db.refresh(updated_node)

    return updated_node


@router.delete(
    "/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Attribute Node",
    description="Delete an attribute node and all its descendants (superuser only)",
    operation_id="deleteAttributeNode",
    responses={
        204: {
            "description": "Attribute node successfully deleted",
        },
        404: {
            "description": "Attribute node not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def delete_attribute_node(
    node_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> None:
    """Delete attribute node and all descendants (superuser only).

    This performs a cascade delete that removes the node and all
    its descendants from the database.

    Args:
        node_id (PositiveInt): Attribute node ID
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Raises:
        NotFoundException: If node not found
        AuthorizationException: If user is not superuser

    Example:
        DELETE /api/v1/attribute-nodes/1
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_node_repo = AttributeNodeRepository(db)

    # Get existing node
    node = await attr_node_repo.get(node_id)
    if not node:
        raise NotFoundException("Attribute node not found")

    # Delete node (cascade deletes descendants)
    await attr_node_repo.delete(node_id)
    await db.commit()
