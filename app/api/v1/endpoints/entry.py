"""Entry Page management endpoints.

This module provides REST API endpoints for the Entry Page system including
profile data entry, schema generation, and preview functionality.

Public Variables:
    router: FastAPI router for entry page endpoints

Features:
    - Profile form schema generation
    - Profile data saving and loading
    - Real-time preview generation
    - Conditional field visibility evaluation
    - HTML page rendering for entry pages
    - Authentication and authorization
    - Comprehensive error handling
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import PositiveInt

from app.api.types import CurrentUser, DBSession
from app.core.exceptions import ValidationException
from app.schemas.configuration import Configuration
from app.schemas.entry import ProfileEntryData, ProfilePreviewData, ProfileSchema
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    prefix="/entry",
    tags=["Entry Pages"],
    responses=get_common_responses(401, 500),
)

templates = Jinja2Templates(directory="app/templates")


@router.get(
    "/profile/schema/{manufacturing_type_id}",
    response_model=ProfileSchema,
    summary="Get Profile Form Schema",
    description="Get dynamic form schema for profile data entry based on manufacturing type",
    response_description="Profile form schema with sections and fields",
    operation_id="getProfileSchema",
    responses={
        200: {
            "description": "Successfully retrieved profile schema",
            "content": {
                "application/json": {
                    "example": {
                        "manufacturing_type_id": 1,
                        "sections": [
                            {
                                "title": "Basic Information",
                                "fields": [
                                    {
                                        "name": "type",
                                        "label": "Type",
                                        "data_type": "string",
                                        "required": True,
                                        "ui_component": "dropdown",
                                        "options": ["Frame", "Flying mullion"],
                                    }
                                ],
                            }
                        ],
                        "conditional_logic": {
                            "renovation": {"operator": "equals", "field": "type", "value": "Frame"}
                        },
                    }
                }
            },
        },
        404: {
            "description": "Manufacturing type not found",
        },
        **get_common_responses(401, 500),
    },
)
async def get_profile_schema(
    manufacturing_type_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> ProfileSchema:
    """Get profile form schema for a manufacturing type.

    Generates dynamic form schema based on the attribute hierarchy
    defined for the specified manufacturing type.

    Args:
        manufacturing_type_id (PositiveInt): Manufacturing type ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        ProfileSchema: Generated form schema with sections and conditional logic

    Raises:
        NotFoundException: If manufacturing type not found

    Example:
        GET /api/v1/entry/profile/schema/1
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.get_profile_schema(manufacturing_type_id)


@router.post(
    "/profile/save",
    response_model=Configuration,
    status_code=status.HTTP_201_CREATED,
    summary="Save Profile Data",
    description="Save profile configuration data and create configuration record",
    response_description="Created configuration",
    operation_id="saveProfileData",
    responses={
        201: {
            "description": "Profile data successfully saved",
        },
        404: {
            "description": "Manufacturing type not found",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def save_profile_data(
    profile_data: ProfileEntryData,
    current_user: CurrentUser,
    db: DBSession,
) -> Configuration:
    """Save profile configuration data.

    Validates the profile data against schema rules and creates
    a new configuration with associated selections.

    Args:
        profile_data (ProfileEntryData): Profile data to save
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Configuration: Created configuration

    Raises:
        ValidationException: If validation fails
        NotFoundException: If manufacturing type not found

    Example:
        POST /api/v1/entry/profile/save
        {
            "manufacturing_type_id": 1,
            "name": "Living Room Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
            "width": 48.5
        }
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    try:
        return await entry_service.save_profile_configuration(profile_data, current_user)
    except ValidationException as e:
        import logging

        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Save Profile Validation Error: {str(e)}")
        if hasattr(e, "field_errors") and e.field_errors:
            logger.error(f"Field Errors: {e.field_errors}")
            # Return structured error response with field errors
            raise HTTPException(
                status_code=422,
                detail={
                    "message": e.message,
                    "field_errors": e.field_errors,
                    "error_type": "validation_error",
                },
            )
        else:
            # Return generic validation error
            raise HTTPException(
                status_code=422, detail={"message": str(e), "error_type": "validation_error"}
            )
    except Exception as e:
        import logging

        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Save Profile Unexpected Error: {str(e)}")
        logger.error(f"Error Type: {type(e).__name__}")
        if hasattr(e, "field_errors"):
            logger.error(f"Field Errors: {e.field_errors}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred while saving the configuration",
                "error_type": "server_error",
            },
        )


@router.get(
    "/profile/load/{configuration_id}",
    response_model=ProfileEntryData,
    summary="Load Profile Data",
    description="Load profile configuration data and populate form fields",
    response_description="Profile data for form population",
    operation_id="loadProfileData",
    responses={
        200: {
            "description": "Profile data successfully loaded",
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
async def load_profile_data(
    configuration_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> ProfileEntryData:
    """Load profile configuration data for form population.

    Retrieves the configuration and its selections, then populates
    the form data structure for editing.

    Args:
        configuration_id (PositiveInt): Configuration ID to load
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        ProfileEntryData: Populated form data

    Raises:
        NotFoundException: If configuration not found
        AuthorizationException: If user lacks permission

    Example:
        GET /api/v1/entry/profile/load/123
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.load_profile_configuration(configuration_id, current_user)


@router.get(
    "/profile/preview/{configuration_id}",
    response_model=ProfilePreviewData,
    summary="Get Profile Preview",
    description="Get preview table data for a configuration",
    response_description="Profile preview data with table structure",
    operation_id="getProfilePreview",
    responses={
        200: {
            "description": "Successfully retrieved profile preview",
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
async def get_profile_preview(
    configuration_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> ProfilePreviewData:
    """Get profile preview data for a configuration.

    Generates preview table data matching CSV structure
    for the specified configuration.

    Args:
        configuration_id (PositiveInt): Configuration ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        ProfilePreviewData: Preview data with table structure

    Raises:
        NotFoundException: If configuration not found
        AuthorizationException: If user lacks permission

    Example:
        GET /api/v1/entry/profile/preview/123
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.generate_preview_data(configuration_id, current_user)


@router.post(
    "/profile/evaluate-conditions",
    summary="Evaluate Display Conditions",
    description="Evaluate conditional field visibility based on form data",
    response_description="Field visibility map",
    operation_id="evaluateDisplayConditions",
    responses={
        200: {
            "description": "Successfully evaluated conditions",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def evaluate_display_conditions(
    manufacturing_type_id: PositiveInt,
    form_data: dict[str, Any],
    current_user: CurrentUser,
    db: DBSession,
):
    """Evaluate display conditions for conditional field visibility.

    Evaluates all conditional display rules against the current form data
    to determine which fields should be visible.

    Args:
        manufacturing_type_id (PositiveInt): Manufacturing type ID
        form_data (dict): Current form data
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        dict[str, bool]: Field visibility map

    Example:
        POST /api/v1/entry/profile/evaluate-conditions
        {
            "manufacturing_type_id": 1,
            "form_data": {
                "type": "Frame",
                "opening_system": "sliding"
            }
        }
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    schema = await entry_service.get_profile_schema(manufacturing_type_id)
    return await entry_service.evaluate_display_conditions(form_data, schema)


# HTML Page Endpoints


@router.get(
    "/profile",
    response_class=HTMLResponse,
    summary="Profile Entry Page",
    description="Render the profile data entry page",
    operation_id="profileEntryPage",
    responses={
        200: {
            "description": "Profile entry page rendered successfully",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 500),
    },
)
async def profile_page(
    request: Request,
    current_user: CurrentUser,
    manufacturing_type_id: Annotated[
        PositiveInt | None,
        Query(description="Manufacturing type ID for form generation"),
    ] = None,
) -> HTMLResponse:
    """Render the profile data entry page.

    Displays the profile entry page with dynamic form generation
    and real-time preview capabilities.

    Args:
        request (Request): FastAPI request object
        current_user (User): Current authenticated user
        manufacturing_type_id (PositiveInt | None): Optional manufacturing type ID

    Returns:
        HTMLResponse: Rendered HTML page

    Example:
        GET /api/v1/entry/profile?manufacturing_type_id=1
    """
    from app.services.entry import JAVASCRIPT_CONDITION_EVALUATOR

    context = {
        "request": request,
        "user": current_user,
        "manufacturing_type_id": manufacturing_type_id,
        "page_title": "Profile Entry",
        "active_page": "profile",
        "JAVASCRIPT_CONDITION_EVALUATOR": JAVASCRIPT_CONDITION_EVALUATOR,
    }

    return templates.TemplateResponse("entry/profile.html.jinja", context)


@router.get(
    "/accessories",
    response_class=HTMLResponse,
    summary="Accessories Entry Page",
    description="Render the accessories data entry page (scaffold)",
    operation_id="accessoriesEntryPage",
    responses={
        200: {
            "description": "Accessories entry page rendered successfully",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 500),
    },
)
async def accessories_page(
    request: Request,
    current_user: CurrentUser,
) -> HTMLResponse:
    """Render the accessories data entry page (scaffold).

    Displays a scaffold page for future accessories data entry implementation.

    Args:
        request (Request): FastAPI request object
        current_user (User): Current authenticated user

    Returns:
        HTMLResponse: Rendered HTML page

    Example:
        GET /api/v1/entry/accessories
    """
    context = {
        "request": request,
        "user": current_user,
        "page_title": "Accessories Entry",
        "active_page": "accessories",
    }

    return templates.TemplateResponse("entry/accessories.html.jinja", context)


@router.get(
    "/glazing",
    response_class=HTMLResponse,
    summary="Glazing Entry Page",
    description="Render the glazing data entry page (scaffold)",
    operation_id="glazingEntryPage",
    responses={
        200: {
            "description": "Glazing entry page rendered successfully",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 500),
    },
)
async def glazing_page(
    request: Request,
    current_user: CurrentUser,
) -> HTMLResponse:
    """Render the glazing data entry page (scaffold).

    Displays a scaffold page for future glazing data entry implementation.

    Args:
        request (Request): FastAPI request object
        current_user (User): Current authenticated user

    Returns:
        HTMLResponse: Rendered HTML page

    Example:
        GET /api/v1/entry/glazing
    """
    context = {
        "request": request,
        "user": current_user,
        "page_title": "Glazing Entry",
        "active_page": "glazing",
    }

    return templates.TemplateResponse("entry/glazing.html.jinja", context)
