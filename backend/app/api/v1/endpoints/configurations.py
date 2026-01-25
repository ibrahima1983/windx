"""Configuration management endpoints.

This module provides REST API endpoints for managing product configurations.

Public Variables:
    router: FastAPI router for configuration endpoints

Features:
    - List user's configurations with pagination
    - Get configuration with selections
    - Create new configuration
    - Update configuration details
    - Update attribute selections
    - Delete configuration
    - Authorization checks (users see only their own)
    - OpenAPI documentation with examples
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import PositiveInt

from app.api.types import CurrentUser, DBSession
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.configuration import Configuration
from app.schemas.configuration import (
    Configuration as ConfigurationSchema,
)
from app.schemas.configuration import (
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationWithSelections,
)
from app.schemas.configuration_selection import ConfigurationSelectionCreate
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    tags=["Configurations"],
    responses=get_common_responses(401, 500),
)


@router.get(
    "/",
    response_model=Page[ConfigurationSchema],
    summary="List Configurations",
    description="List user's configurations with pagination. Superusers can see all configurations.",
    response_description="Paginated list of configurations",
    operation_id="listConfigurations",
    responses={
        200: {
            "description": "Successfully retrieved configurations",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "manufacturing_type_id": 1,
                                "customer_id": 42,
                                "name": "Living Room Window",
                                "description": "Bay window facing south",
                                "status": "draft",
                                "reference_code": "WIN-2024-001",
                                "base_price": "200.00",
                                "total_price": "525.00",
                                "calculated_weight": "23.00",
                                "calculated_technical_data": {},
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
async def list_configurations(
    current_user: CurrentUser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    manufacturing_type_id: Annotated[
        PositiveInt | None,
        Query(description="Filter by manufacturing type ID"),
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by status (draft, saved, quoted, ordered)"),
    ] = None,
) -> Page[Configuration]:
    """List user's configurations with filtering.

    Regular users see only their own configurations.
    Superusers can see all configurations.

    Args:
        current_user (User): Current authenticated user
        params (PaginationParams): Pagination parameters
        db (AsyncSession): Database session
        manufacturing_type_id (PositiveInt | None): Filter by manufacturing type
        status_filter (str | None): Filter by status

    Returns:
        Page[Configuration]: Paginated list of configurations

    Example:
        GET /api/v1/configurations?status=draft&manufacturing_type_id=1
    """
    from app.core.pagination import paginate
    from app.services.configuration import ConfigurationService

    config_service = ConfigurationService(db)

    # Build filtered query with authorization
    query = config_service.get_user_configurations_query(
        user=current_user,
        manufacturing_type_id=manufacturing_type_id,
        status=status_filter,
    )

    return await paginate(db, query, params)


@router.get(
    "/{config_id}",
    response_model=ConfigurationWithSelections,
    summary="Get Configuration",
    description="Get a configuration with all its selections",
    response_description="Configuration with selections",
    operation_id="getConfiguration",
    responses={
        200: {
            "description": "Successfully retrieved configuration",
        },
        403: {
            "description": "Not authorized to access this configuration",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 500),
    },
)
async def get_configuration(
    config_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> Configuration:
    """Get configuration with selections.

    Users can only access their own configurations unless they are superusers.

    Args:
        config_id (PositiveInt): Configuration ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Configuration: Configuration with selections

    Raises:
        NotFoundException: If configuration not found
        AuthorizationException: If user lacks permission
    """
    from app.services.configuration import ConfigurationService

    config_service = ConfigurationService(db)
    return await config_service.get_configuration_with_auth(config_id, current_user)


@router.post(
    "/",
    response_model=ConfigurationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create Configuration",
    description="Create a new product configuration",
    response_description="Created configuration",
    operation_id="createConfiguration",
    responses={
        201: {
            "description": "Configuration successfully created",
        },
        404: {
            "description": "Manufacturing type not found",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def create_configuration(
    config_in: ConfigurationCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> Configuration:
    """Create a new configuration.

    Args:
        config_in (ConfigurationCreate): Configuration creation data
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Configuration: Created configuration

    Raises:
        NotFoundException: If manufacturing type not found

    Example:
        POST /api/v1/configurations
        {
            "manufacturing_type_id": 1,
            "name": "Living Room Window",
            "description": "Bay window facing south",
            "selections": []
        }
    """
    from app.services.configuration import ConfigurationService

    config_service = ConfigurationService(db)
    return await config_service.create_configuration(config_in, current_user)


@router.patch(
    "/{config_id}",
    response_model=ConfigurationSchema,
    summary="Update Configuration",
    description="Update configuration name and description",
    response_description="Updated configuration",
    operation_id="updateConfiguration",
    responses={
        200: {
            "description": "Configuration successfully updated",
        },
        403: {
            "description": "Not authorized to update this configuration",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def update_configuration(
    config_id: PositiveInt,
    config_update: ConfigurationUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> Configuration:
    """Update configuration details.

    Users can only update their own configurations unless they are superusers.

    Args:
        config_id (PositiveInt): Configuration ID
        config_update (ConfigurationUpdate): Update data
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Configuration: Updated configuration

    Raises:
        NotFoundException: If configuration not found
        AuthorizationException: If user lacks permission

    Example:
        PATCH /api/v1/configurations/1
        {
            "name": "Updated Name",
            "description": "Updated description"
        }
    """
    from app.services.configuration import ConfigurationService

    config_service = ConfigurationService(db)
    return await config_service.update_configuration(config_id, config_update, current_user)


@router.patch(
    "/{config_id}/selections",
    response_model=ConfigurationWithSelections,
    summary="Update Configuration Selections",
    description="Update attribute selections for a configuration",
    response_description="Configuration with updated selections",
    operation_id="updateConfigurationSelections",
    responses={
        200: {
            "description": "Selections successfully updated",
        },
        403: {
            "description": "Not authorized to update this configuration",
        },
        404: {
            "description": "Configuration or attribute node not found",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def update_configuration_selections(
    config_id: PositiveInt,
    selections: list[ConfigurationSelectionCreate],
    current_user: CurrentUser,
    db: DBSession,
) -> Configuration:
    """Update configuration selections.

    Replaces all existing selections with the provided list.
    Automatically recalculates total price and weight.

    Args:
        config_id (PositiveInt): Configuration ID
        selections (list[ConfigurationSelectionCreate]): New selections
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Configuration: Configuration with updated selections

    Raises:
        NotFoundException: If configuration or attribute node not found
        AuthorizationException: If user lacks permission

    Example:
        PATCH /api/v1/configurations/1/selections
        [
            {
                "attribute_node_id": 7,
                "string_value": "Aluminum"
            },
            {
                "attribute_node_id": 12,
                "numeric_value": 48.5
            }
        ]
    """
    from app.services.configuration import ConfigurationService

    config_service = ConfigurationService(db)
    return await config_service.update_selections(config_id, selections, current_user)


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Configuration",
    description="Delete a configuration and all its selections",
    operation_id="deleteConfiguration",
    responses={
        204: {
            "description": "Configuration successfully deleted",
        },
        403: {
            "description": "Not authorized to delete this configuration",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 500),
    },
)
async def delete_configuration(
    config_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete configuration.

    Users can only delete their own configurations unless they are superusers.
    Cascade deletes all selections.

    Args:
        config_id (PositiveInt): Configuration ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Raises:
        NotFoundException: If configuration not found
        AuthorizationException: If user lacks permission

    Example:
        DELETE /api/v1/configurations/1
    """
    from app.services.configuration import ConfigurationService

    config_service = ConfigurationService(db)
    await config_service.delete_configuration(config_id, current_user)
