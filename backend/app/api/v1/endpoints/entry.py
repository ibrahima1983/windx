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
from fastapi import APIRouter, File as FastAPIFile, HTTPException, UploadFile, status
from pydantic import PositiveInt

from app.api.types import CurrentUser, DBSession
from app.core.exceptions import ValidationException
from app.schemas.configuration import Configuration
from app.schemas.entry import (
    InlineEditRequest,
    PreviewTable,
    ProfileEntryData,
    ProfilePreviewData,
    ProfileSchema,
)
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    prefix="/entry",
    tags=["Entry Pages"],
    responses=get_common_responses(401, 500),
)


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


@router.get(
    "/profile/headers/{manufacturing_type_id}",
    response_model=list[str],
    summary="Get Profile Preview Headers",
    description="Get ordered list of headers for profile preview table",
    operation_id="getProfileHeaders",
)
async def get_profile_headers(
    manufacturing_type_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
    page_type: str = "profile",
) -> list[str]:
    """Get dynamic preview headers for a manufacturing type."""
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.generate_preview_headers(manufacturing_type_id, page_type)


@router.get(
    "/profile/header-mapping/{manufacturing_type_id}",
    response_model=dict[str, str],
    summary="Get Profile Header Mapping",
    description="Get mapping from preview headers to internal field names",
    operation_id="getProfileHeaderMapping",
)
async def get_profile_header_mapping(
    manufacturing_type_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
    page_type: str = "profile",
) -> dict[str, str]:
    """Get dynamic header-to-field mapping for a manufacturing type."""
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.generate_header_mapping(manufacturing_type_id)


@router.get(
    "/profile/previews/{manufacturing_type_id}",
    response_model=PreviewTable,
    summary="List Profile Previews",
    description="Get all profile configuration previews for a manufacturing type",
    operation_id="listProfilePreviews",
)
async def list_profile_previews(
    manufacturing_type_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> PreviewTable:
    """List all profile configuration previews."""
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.list_previews(manufacturing_type_id, current_user)



@router.patch(
    "/profile/preview/{configuration_id}/update-cell",
    response_model=Configuration,
    summary="Update Preview Cell",
    description="Update a specific field in a configuration from table preview",
    operation_id="updateProfileCell",
)
async def update_profile_cell(
    configuration_id: PositiveInt,
    edit_request: InlineEditRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> Configuration:
    """Update a specific field in a configuration."""
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.update_preview_value(
        configuration_id, edit_request.field, edit_request.value, current_user
    )


@router.post(
    "/upload-image",
    summary="Upload Image",
    description="Upload an image file for a configuration or entity",
    operation_id="uploadImage",
)
async def upload_image(
    file: UploadFile = FastAPIFile(...),
    current_user: CurrentUser = None,
    db: DBSession = None,
):
    """Upload an image file for a configuration or entity."""
    import os
    import shutil
    import uuid
    from pathlib import Path

    # Define upload directory relative to this file
    # File is in backend/app/api/v1/endpoints/entry.py
    # Parent (endpoints) -> Parent (v1) -> Parent (api) -> Parent (app) -> static
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    upload_dir = base_dir / "static" / "uploads"

    # Ensure directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename to prevent collisions
    ext = os.path.splitext(file.filename)[1]
    new_filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / new_filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Return relative URL from static mount point
        return {
            "url": f"static/uploads/{new_filename}",
            "filename": file.filename,
            "id": new_filename,
            "success": True,
        }
    except Exception as e:
        import logging

        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Upload Image Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )


@router.delete(
    "/profile/configurations/bulk",
    summary="Bulk Delete Profile Configurations",
    description="Delete multiple profile configurations at once (superuser only)",
    response_description="Bulk delete operation result",
    operation_id="bulkDeleteProfileConfigurations",
    responses={
        200: {
            "description": "Bulk delete completed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Bulk delete completed",
                        "deleted_count": 3,
                        "error_count": 0,
                        "total_requested": 3
                    }
                }
            },
        },
        400: {
            "description": "Invalid request (empty ID list)",
        },
        403: {
            "description": "Not authorized (superuser required)",
        },
        **get_common_responses(401, 500),
    },
)
async def bulk_delete_profile_configurations(
    configuration_ids: list[PositiveInt],
    current_user: CurrentUser,
    db: DBSession,
) -> dict[str, Any]:
    """Bulk delete multiple profile configurations.

    Deletes multiple configurations at once. Only superusers can perform
    bulk delete operations. The operation will attempt to delete all
    provided configurations and return a summary of the results.

    Args:
        configuration_ids (list[PositiveInt]): List of configuration IDs to delete
        current_user (User): Current authenticated user (must be superuser)
        db (AsyncSession): Database session

    Returns:
        dict[str, Any]: Bulk delete operation result with counts

    Raises:
        HTTPException: If user is not superuser or request is invalid

    Example:
        DELETE /api/v1/admin/entry/profile/configurations/bulk
        [1, 2, 3, 4, 5]
    """
    from app.services.entry import EntryService

    # Validate request
    if not configuration_ids:
        raise HTTPException(
            status_code=400,
            detail="No configuration IDs provided for bulk delete"
        )

    entry_service = EntryService(db)
    return await entry_service.bulk_delete_profile_configurations(configuration_ids, current_user)



