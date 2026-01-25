"""Configuration Template management endpoints.

This module provides REST API endpoints for managing configuration templates.

Public Variables:
    router: FastAPI router for template endpoints

Features:
    - List public templates with pagination
    - Get template with selections
    - Create template from configuration (data entry users)
    - Apply template to new configuration
    - Authorization checks (public read, restricted write)
    - OpenAPI documentation with examples
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import PositiveInt

from app.api.types import CurrentSuperuser, CurrentUser, DBSession
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.configuration_template import ConfigurationTemplate
from app.schemas.configuration_template import (
    ConfigurationTemplate as TemplateSchema,
)
from app.schemas.configuration_template import (
    ConfigurationTemplateCreate,
    ConfigurationTemplateWithSelections,
)
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    tags=["Templates"],
    responses=get_common_responses(401, 500),
)


@router.get(
    "/",
    response_model=Page[TemplateSchema],
    summary="List Templates",
    description="List public templates with pagination",
    response_description="Paginated list of templates",
    operation_id="listTemplates",
    responses={
        200: {
            "description": "Successfully retrieved templates",
        },
        **get_common_responses(401, 500),
    },
)
async def list_templates(
    current_user: CurrentUser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    manufacturing_type_id: Annotated[
        PositiveInt | None,
        Query(description="Filter by manufacturing type ID"),
    ] = None,
    template_type: Annotated[
        str | None,
        Query(description="Filter by template type (standard, premium, economy, custom)"),
    ] = None,
) -> Page[ConfigurationTemplate]:
    """List public templates with filtering.

    Args:
        current_user (User): Current authenticated user
        params (PaginationParams): Pagination parameters
        db (AsyncSession): Database session
        manufacturing_type_id (PositiveInt | None): Filter by manufacturing type
        template_type (str | None): Filter by template type

    Returns:
        Page[ConfigurationTemplate]: Paginated list of templates

    Example:
        GET /api/v1/templates?manufacturing_type_id=1&template_type=standard
    """
    from app.core.pagination import paginate
    from app.repositories.configuration_template import ConfigurationTemplateRepository

    template_repo = ConfigurationTemplateRepository(db)

    # Build filtered query (public templates only for regular users)
    query = template_repo.get_filtered(
        is_public=True if not current_user.is_superuser else None,
        manufacturing_type_id=manufacturing_type_id,
        template_type=template_type,
        is_active=True,
    )

    return await paginate(db, query, params)


@router.get(
    "/{template_id}",
    response_model=ConfigurationTemplateWithSelections,
    summary="Get Template",
    description="Get a template with all its selections",
    response_description="Template with selections",
    operation_id="getTemplate",
    responses={
        200: {
            "description": "Successfully retrieved template",
        },
        404: {
            "description": "Template not found",
        },
        **get_common_responses(401, 500),
    },
)
async def get_template(
    template_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> ConfigurationTemplate:
    """Get template with selections.

    Args:
        template_id (PositiveInt): Template ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        ConfigurationTemplate: Template with selections

    Raises:
        NotFoundException: If template not found
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.configuration_template import ConfigurationTemplateRepository

    template_repo = ConfigurationTemplateRepository(db)
    template = await template_repo.get_with_selections(template_id)

    if not template:
        raise NotFoundException("Template not found")

    return template


@router.post(
    "/",
    response_model=TemplateSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create Template",
    description="Create a new template from a configuration (superuser only)",
    response_description="Created template",
    operation_id="createTemplate",
    responses={
        201: {
            "description": "Template successfully created",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def create_template(
    template_in: ConfigurationTemplateCreate,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> ConfigurationTemplate:
    """Create a new template (superuser only).

    Args:
        template_in (ConfigurationTemplateCreate): Template creation data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        ConfigurationTemplate: Created template

    Raises:
        NotFoundException: If configuration not found
        AuthorizationException: If user is not superuser

    Example:
        POST /api/v1/templates
        {
            "name": "Standard Window",
            "description": "Most popular configuration",
            "manufacturing_type_id": 1,
            "template_type": "standard",
            "is_public": true
        }
    """
    from app.services.template import TemplateService

    template_service = TemplateService(db)
    return await template_service.create_template(template_in, current_superuser)


@router.post(
    "/{template_id}/apply",
    response_model=dict,
    summary="Apply Template",
    description="Apply a template to create a new configuration",
    response_description="Created configuration ID",
    operation_id="applyTemplate",
    responses={
        200: {
            "description": "Template successfully applied",
            "content": {
                "application/json": {
                    "example": {"configuration_id": 123, "message": "Template applied successfully"}
                }
            },
        },
        404: {
            "description": "Template not found",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def apply_template(
    template_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
    configuration_name: Annotated[
        str | None,
        Query(description="Name for the new configuration"),
    ] = None,
) -> dict:
    """Apply template to create a new configuration.

    Args:
        template_id (PositiveInt): Template ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session
        configuration_name (str | None): Name for new configuration

    Returns:
        dict: Created configuration ID and message

    Raises:
        NotFoundException: If template not found

    Example:
        POST /api/v1/templates/1/apply?configuration_name=My Window
    """
    from app.services.template import TemplateService

    template_service = TemplateService(db)
    config = await template_service.apply_template(template_id, current_user, configuration_name)

    return {"configuration_id": config.id, "message": "Template applied successfully"}
