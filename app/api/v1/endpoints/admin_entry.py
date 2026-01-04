"""Admin Entry Page management endpoints.

This module provides admin-only endpoints for the Entry Page system including
profile data entry, schema generation, and preview functionality within the admin interface.

Public Variables:
    router: FastAPI router for admin entry page endpoints

Features:
    - Profile form schema generation (admin interface)
    - Profile data saving and loading (admin interface)
    - Real-time preview generation (admin interface)
    - Conditional field visibility evaluation (admin interface)
    - HTML page rendering for admin entry pages
    - Superuser authentication and authorization
    - Comprehensive error handling
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import PositiveInt

from app.api.deps import get_admin_context
from app.api.types import CurrentSuperuser, DBSession
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
    tags=["Admin Entry"],
    responses=get_common_responses(401, 403, 500),
)

templates = Jinja2Templates(directory="app/templates")


@router.get(
    "/profile/schema/{manufacturing_type_id}",
    response_model=ProfileSchema,
    summary="Get Profile Form Schema (Admin)",
    description="Get dynamic form schema for profile data entry based on manufacturing type and page type (admin interface)",
    response_description="Profile form schema with sections and fields",
    operation_id="getAdminProfileSchema",
    responses={
        200: {
            "description": "Successfully retrieved profile schema",
        },
        404: {
            "description": "Manufacturing type not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def get_profile_schema(
    manufacturing_type_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    page_type: Annotated[
        str,
        Query(description="Page type: profile, accessories, glazing"),
    ] = "profile",
) -> ProfileSchema:
    """Get profile form schema for a manufacturing type and page type (admin interface).

    Generates dynamic form schema based on the attribute hierarchy
    defined for the specified manufacturing type and page type.

    Args:
        manufacturing_type_id (PositiveInt): Manufacturing type ID
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session
        page_type (str): Page type (profile, accessories, glazing)

    Returns:
        ProfileSchema: Generated form schema with sections and conditional logic

    Raises:
        NotFoundException: If manufacturing type not found

    Example:
        GET /api/v1/admin/entry/profile/schema/1?page_type=profile
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.get_profile_schema(manufacturing_type_id, page_type)


@router.get(
    "/profile/headers/{manufacturing_type_id}",
    response_model=list[str],
    summary="Get Dynamic Preview Headers (Admin)",
    description="Get dynamic preview headers for a manufacturing type and page type based on attribute nodes",
    response_description="List of preview headers in correct order",
    operation_id="getAdminPreviewHeaders",
    responses={
        200: {
            "description": "Successfully retrieved preview headers",
        },
        404: {
            "description": "Manufacturing type not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def get_preview_headers(
    manufacturing_type_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    page_type: Annotated[
        str,
        Query(description="Page type: profile, accessories, glazing"),
    ] = "profile",
) -> list[str]:
    """Get dynamic preview headers for a manufacturing type and page type (admin interface).

    Generates dynamic preview headers based on the attribute hierarchy
    defined for the specified manufacturing type and page type, respecting sort_order.

    Args:
        manufacturing_type_id (PositiveInt): Manufacturing type ID
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session
        page_type (str): Page type (profile, accessories, glazing)

    Returns:
        list[str]: Ordered list of preview headers

    Raises:
        NotFoundException: If manufacturing type not found

    Example:
        GET /api/v1/admin/entry/profile/headers/1?page_type=profile
        Response: ["id", "Name", "Type", "Material", "Company", ...]
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.generate_preview_headers(manufacturing_type_id, page_type)


@router.post(
    "/profile/save",
    response_model=Configuration,
    status_code=status.HTTP_201_CREATED,
    summary="Save Profile Data (Admin)",
    description="Save profile configuration data and create configuration record (admin interface)",
    response_description="Created configuration",
    operation_id="saveAdminProfileData",
    responses={
        201: {
            "description": "Profile data successfully saved",
        },
        404: {
            "description": "Manufacturing type not found",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def save_profile_data(
    profile_data: ProfileEntryData,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    page_type: Annotated[
        str,
        Query(description="Page type: profile, accessories, glazing"),
    ] = "profile",
) -> Configuration:
    """Save profile configuration data (admin interface).

    Validates the profile data against schema rules and creates
    a new configuration with associated selections.

    Args:
        profile_data (ProfileEntryData): Profile data to save
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        Configuration: Created configuration

    Raises:
        ValidationException: If validation fails
        NotFoundException: If manufacturing type not found

    Example:
        POST /api/v1/admin/entry/profile/save
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
        return await entry_service.save_profile_configuration(profile_data, current_superuser, page_type)
    except ValidationException as e:
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Save Profile Validation Error: {str(e)}")
        if hasattr(e, 'field_errors') and e.field_errors:
            logger.error(f"Field Errors: {e.field_errors}")
            # Return structured error response with field errors
            raise HTTPException(
                status_code=422,
                detail={
                    "message": e.message,
                    "field_errors": e.field_errors,
                    "error_type": "validation_error"
                }
            )
        else:
            # Return generic validation error
            raise HTTPException(
                status_code=422,
                detail={
                    "message": str(e),
                    "error_type": "validation_error"
                }
            )
    except Exception as e:
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Save Profile Unexpected Error: {str(e)}")
        logger.error(f"Error Type: {type(e).__name__}")
        if hasattr(e, 'field_errors'):
             logger.error(f"Field Errors: {e.field_errors}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred while saving the configuration",
                "error_type": "server_error"
            }
        )


@router.get(
    "/profile/load/{configuration_id}",
    response_model=ProfileEntryData,
    summary="Load Profile Data (Admin)",
    description="Load profile configuration data and populate form fields (admin interface)",
    response_description="Profile data for form population",
    operation_id="loadAdminProfileData",
    responses={
        200: {
            "description": "Profile data successfully loaded",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def load_profile_data(
    configuration_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> ProfileEntryData:
    """Load profile configuration data for form population (admin interface).

    Retrieves the configuration and its selections, then populates
    the form data structure for editing.

    Args:
        configuration_id (PositiveInt): Configuration ID to load
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        ProfileEntryData: Populated form data

    Raises:
        NotFoundException: If configuration not found

    Example:
        GET /api/v1/admin/entry/profile/load/123
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.load_profile_configuration(configuration_id, current_superuser)


@router.get(
    "/profile/preview/{configuration_id}",
    response_model=ProfilePreviewData,
    summary="Get Profile Preview (Admin)",
    description="Get preview table data for a configuration (admin interface)",
    response_description="Profile preview data with table structure",
    operation_id="getAdminProfilePreview",
    responses={
        200: {
            "description": "Successfully retrieved profile preview",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def get_profile_preview(
    configuration_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> ProfilePreviewData:
    """Get profile preview data for a configuration (admin interface).

    Generates preview table data matching CSV structure
    for the specified configuration.

    Args:
        configuration_id (PositiveInt): Configuration ID
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        ProfilePreviewData: Preview data with table structure

    Raises:
        NotFoundException: If configuration not found

    Example:
        GET /api/v1/admin/entry/profile/preview/123
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.generate_preview_data(configuration_id, current_superuser)


@router.get(
    "/profile/previews/{manufacturing_type_id}",
    response_model=PreviewTable,
    summary="List Profile Previews (Admin)",
    description="List all profile configurations for a manufacturing type (admin interface)",
    response_description="Table with all configurations",
    operation_id="listAdminProfilePreviews",
    responses={
        200: {
            "description": "Successfully retrieved profile previews",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def list_profile_previews(
    manufacturing_type_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> PreviewTable:
    """List all profile configuration previews (admin interface)."""
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.list_previews(manufacturing_type_id, current_superuser)


@router.patch(
    "/profile/preview/{configuration_id}/update-cell",
    response_model=Configuration,
    summary="Update Preview Cell (Admin)",
    description="Update a single field in a configuration from the table preview (admin interface)",
    response_description="Updated configuration",
    operation_id="updateAdminPreviewCell",
    responses={
        200: {
            "description": "Cell successfully updated",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def update_preview_cell(
    configuration_id: PositiveInt,
    edit_req: InlineEditRequest,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> Configuration:
    """Update a specific field in a configuration from the preview table (admin interface)."""
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.update_preview_value(
        configuration_id, edit_req.field, edit_req.value, current_superuser
    )


@router.delete(
    "/profile/configuration/{configuration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Configuration (Admin)",
    description="Delete a profile configuration (admin interface)",
    operation_id="deleteAdminConfiguration",
    responses={
        204: {
            "description": "Configuration successfully deleted",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def delete_configuration(
    configuration_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> None:
    """Delete a configuration (admin interface)."""
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    await entry_service.delete_profile_configuration(configuration_id, current_superuser)


@router.delete(
    "/profile/configurations/bulk",
    summary="Bulk Delete Configurations (Admin)",
    description="Delete multiple profile configurations in bulk (admin interface)",
    operation_id="bulkDeleteAdminConfigurations",
    responses={
        200: {
            "description": "Bulk delete completed",
            "content": {
                "application/json": {
                    "example": {
                        "success_count": 3,
                        "error_count": 1,
                        "total_requested": 4,
                        "errors": ["Configuration 999 not found"]
                    }
                }
            }
        },
        400: {
            "description": "Invalid request - no IDs provided",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def bulk_delete_configurations(
    configuration_ids: list[PositiveInt],
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> dict[str, Any]:
    """Bulk delete multiple configurations (admin interface).
    
    Args:
        configuration_ids: List of configuration IDs to delete
        current_superuser: Current authenticated superuser
        db: Database session
        
    Returns:
        dict: Result with success/error counts and details
        
    Example:
        DELETE /api/v1/admin/entry/profile/configurations/bulk
        [123, 124, 125]
    """
    from app.services.entry import EntryService

    if not configuration_ids:
        raise HTTPException(
            status_code=400,
            detail="No configuration IDs provided"
        )

    entry_service = EntryService(db)
    return await entry_service.bulk_delete_profile_configurations(configuration_ids, current_superuser)


@router.post(
    "/upload-image",
    summary="Upload Image File (Admin)",
    description="Upload an image file for profile entry fields (admin interface)",
    response_description="Upload result with filename",
    operation_id="uploadAdminImage",
    responses={
        200: {
            "description": "Image uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "filename": "uploaded_image_123456.jpg",
                        "url": "https://example.com/path/to/image.jpg",
                        "message": "Image uploaded successfully"
                    }
                }
            }
        },
        400: {
            "description": "Invalid file or upload error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Invalid file type. Only images are allowed."
                    }
                }
            }
        }
    },
)
async def upload_image(
    request: Request,
    current_superuser: CurrentSuperuser,
) -> dict[str, Any]:
    """Upload an image file for profile entry fields (admin interface)."""
    from app.services.storage import get_storage_service
    
    try:
        # Parse multipart form data
        form_data = await request.form()
        file = form_data.get("file")
        
        print(f"🦆 [BACKEND DEBUG] Upload endpoint called")
        print(f"🦆 [BACKEND DEBUG] form_data keys: {list(form_data.keys())}")
        print(f"🦆 [BACKEND DEBUG] file object: {file}")
        print(f"🦆 [BACKEND DEBUG] file type: {type(file)}")
        
        if not file:
            print(f"🦆 [BACKEND DEBUG] ❌ No file in form data")
            return {
                "success": False,
                "error": "No file provided"
            }
        
        # Check if it's a proper file object
        if not hasattr(file, 'filename') or not hasattr(file, 'read'):
            print(f"🦆 [BACKEND DEBUG] ❌ Invalid file object - missing filename or read method")
            print(f"🦆 [BACKEND DEBUG] file attributes: {dir(file)}")
            return {
                "success": False,
                "error": "Invalid file object"
            }
        
        print(f"🦆 [BACKEND DEBUG] file.filename: {file.filename}")
        print(f"🦆 [BACKEND DEBUG] file content_type: {getattr(file, 'content_type', 'unknown')}")
        
        # Use the storage service to handle the upload
        storage_service = get_storage_service()
        print(f"🦆 [BACKEND DEBUG] Calling storage service upload_file...")
        result = await storage_service.upload_file(file)
        
        print(f"🦆 [BACKEND DEBUG] Upload result: {result}")
        
        if result.success:
            return {
                "success": True,
                "filename": result.filename,
                "url": result.url,
                "message": "Image uploaded successfully"
            }
        else:
            return {
                "success": False,
                "error": result.error or "Upload failed"
            }
        
    except Exception as e:
        print(f"🦆 [BACKEND DEBUG] ❌ Exception in upload endpoint: {e}")
        print(f"🦆 [BACKEND DEBUG] Exception type: {type(e)}")
        import traceback
        print(f"🦆 [BACKEND DEBUG] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}"
        }



@router.post(
    "/profile/evaluate-conditions",
    summary="Evaluate Display Conditions (Admin)",
    description="Evaluate conditional field visibility based on form data (admin interface)",
    response_description="Field visibility map",
    operation_id="evaluateAdminDisplayConditions",
    responses={
        200: {
            "description": "Successfully evaluated conditions",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def evaluate_display_conditions(
    manufacturing_type_id: PositiveInt,
    form_data: dict[str, Any],
    current_superuser: CurrentSuperuser,
    db: DBSession,
):
    """Evaluate display conditions for conditional field visibility (admin interface).

    Evaluates all conditional display rules against the current form data
    to determine which fields should be visible.

    Args:
        manufacturing_type_id (PositiveInt): Manufacturing type ID
        form_data (dict): Current form data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        dict[str, bool]: Field visibility map

    Example:
        POST /api/v1/admin/entry/profile/evaluate-conditions
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


@router.post(
    "/profile/add-option",
    response_model=dict[str, Any],
    summary="Add New Option (Admin)",
    description="Add a new option to an attribute field (admin interface)",
    response_description="Result of adding the new option",
    operation_id="addAdminFieldOption",
    responses={
        200: {
            "description": "Option added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Option 'New Material' added successfully",
                        "option_id": 123,
                        "field_name": "material",
                        "option_value": "New Material"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request or duplicate option",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def add_field_option(
    manufacturing_type_id: PositiveInt,
    field_name: str,
    option_value: str,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    page_type: Annotated[
        str,
        Query(description="Page type: profile, accessories, glazing"),
    ] = "profile",
) -> dict[str, Any]:
    """Add a new option to an attribute field (admin interface).

    Creates a new attribute node of type 'option' under the specified field.

    Args:
        manufacturing_type_id (PositiveInt): Manufacturing type ID
        field_name (str): Name of the field to add option to
        option_value (str): Value of the new option
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session
        page_type (str): Page type (profile, accessories, glazing)

    Returns:
        dict: Result with success status and details

    Example:
        POST /api/v1/admin/entry/profile/add-option?manufacturing_type_id=1&field_name=material&option_value=Steel&page_type=profile
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.add_field_option(
        manufacturing_type_id, field_name, option_value, page_type
    )


@router.delete(
    "/profile/remove-option/{option_id}",
    response_model=dict[str, Any],
    summary="Remove Option (Admin)",
    description="Remove an option from an attribute field (admin interface)",
    response_description="Result of removing the option",
    operation_id="removeAdminFieldOption",
    responses={
        200: {
            "description": "Option removed successfully",
        },
        404: {
            "description": "Option not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def remove_field_option(
    option_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> dict[str, Any]:
    """Remove an option from an attribute field (admin interface).

    Deletes the attribute node of type 'option' with the specified ID.

    Args:
        option_id (PositiveInt): ID of the option to remove
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        dict: Result with success status and details

    Example:
        DELETE /api/v1/admin/entry/profile/remove-option/123
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.remove_field_option(option_id)


@router.delete(
    "/profile/remove-option-by-name",
    response_model=dict[str, Any],
    summary="Remove Option by Name (Admin)",
    description="Remove an option from an attribute field by name (admin interface)",
    response_description="Result of removing the option",
    operation_id="removeAdminFieldOptionByName",
    responses={
        200: {
            "description": "Option removed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Option 'Steel' removed successfully from field 'material'",
                        "option_id": 123,
                        "field_name": "material",
                        "option_value": "Steel"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request or option not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def remove_field_option_by_name(
    manufacturing_type_id: PositiveInt,
    field_name: str,
    option_value: str,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    page_type: Annotated[
        str,
        Query(description="Page type: profile, accessories, glazing"),
    ] = "profile",
) -> dict[str, Any]:
    """Remove an option from an attribute field by name (admin interface).

    Finds and deletes the attribute node of type 'option' with the specified name.

    Args:
        manufacturing_type_id (PositiveInt): Manufacturing type ID
        field_name (str): Name of the field to remove option from
        option_value (str): Value of the option to remove
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session
        page_type (str): Page type (profile, accessories, glazing)

    Returns:
        dict: Result with success status and details

    Example:
        DELETE /api/v1/admin/entry/profile/remove-option-by-name?manufacturing_type_id=1&field_name=material&option_value=Steel&page_type=profile
    """
    from app.services.entry import EntryService

    entry_service = EntryService(db)
    return await entry_service.remove_field_option_by_name(
        manufacturing_type_id, field_name, option_value, page_type
    )


# HTML Page Endpoints


@router.get(
    "/profile",
    response_class=HTMLResponse,
    summary="Admin Profile Entry Page",
    description="Render the admin profile data entry page",
    operation_id="adminProfileEntryPage",
    responses={
        200: {
            "description": "Admin profile entry page rendered successfully",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 403, 500),
    },
)
async def profile_page(
    request: Request,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    manufacturing_type_id: Annotated[
        PositiveInt | None,
        Query(description="Manufacturing type ID for form generation"),
    ] = None,
    page_type: Annotated[
        str,
        Query(description="Page type: profile, accessories, glazing"),
    ] = "profile",
) -> HTMLResponse:
    """Render the admin profile data entry page.

    Displays the profile entry page with dynamic form generation
    and real-time preview capabilities within the admin interface.

    Args:
        request (Request): FastAPI request object
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session
        manufacturing_type_id (PositiveInt | None): Optional manufacturing type ID
        page_type (str): Page type (profile, accessories, glazing)

    Returns:
        HTMLResponse: Rendered HTML page

    Example:
        GET /api/v1/admin/entry/profile?manufacturing_type_id=1&page_type=profile
    """
    from app.core.manufacturing_type_resolver import ManufacturingTypeResolver
    from app.services.entry import JAVASCRIPT_CONDITION_EVALUATOR

    # Validate page_type
    if not ManufacturingTypeResolver.validate_page_type(page_type):
        return templates.TemplateResponse(
            request,
            "admin/error.html.jinja",
            get_admin_context(
                request,
                current_superuser,
                error_message=f"Invalid page type '{page_type}'. Must be one of: profile, accessories, glazing",
                page_title="Invalid Page Type",
            ),
            status_code=400,
        )

    # If no manufacturing_type_id provided, resolve the default for this page type
    if manufacturing_type_id is None:
        default_type = await ManufacturingTypeResolver.get_default_for_page_type(
            db, page_type, "window"
        )
        if default_type:
            manufacturing_type_id = default_type.id
        else:
            # No manufacturing types exist - show error page or redirect to setup
            return templates.TemplateResponse(
                request,
                "admin/error.html.jinja",
                get_admin_context(
                    request,
                    current_superuser,
                    error_message=f"No manufacturing types found for {page_type} page. Please run the setup script.",
                    page_title="Setup Required",
                ),
                status_code=503,
            )

    # Determine the template based on page_type
    template_map = {
        "profile": "admin/entry/profile.html.jinja",
        "accessories": "admin/entry/accessories.html.jinja", 
        "glazing": "admin/entry/glazing.html.jinja",
    }
    
    template_name = template_map.get(page_type, "admin/entry/profile.html.jinja")
    
    # Determine active page for navigation
    active_page_map = {
        "profile": "entry_profile",
        "accessories": "entry_accessories",
        "glazing": "entry_glazing",
    }
    
    active_page = active_page_map.get(page_type, "entry_profile")

    return templates.TemplateResponse(
        request,
        template_name,
        get_admin_context(
            request,
            current_superuser,
            active_page=active_page,
            manufacturing_type_id=manufacturing_type_id,
            page_type=page_type,
            page_title=f"{page_type.title()} Entry",
            JAVASCRIPT_CONDITION_EVALUATOR=JAVASCRIPT_CONDITION_EVALUATOR,
            can_edit=True,  # TODO: Implement granular RBAC check
            can_delete=True,  # TODO: Implement granular RBAC check
        ),
    )



@router.get(
    "/accessories",
    response_class=HTMLResponse,
    summary="Admin Accessories Entry Page",
    description="Render the admin accessories data entry page",
    operation_id="adminAccessoriesEntryPage",
    responses={
        200: {
            "description": "Admin accessories entry page rendered successfully",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 403, 500),
    },
)
async def accessories_page(
    request: Request,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    manufacturing_type_id: Annotated[
        PositiveInt | None,
        Query(description="Manufacturing type ID for form generation"),
    ] = None,
    type: Annotated[
        str,
        Query(description="Manufacturing category: window, door"),
    ] = "window",
) -> HTMLResponse:
    """Render the admin accessories data entry page.

    Displays the accessories entry page with dynamic form generation
    and real-time preview capabilities within the admin interface.

    Args:
        request (Request): FastAPI request object
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session
        manufacturing_type_id (PositiveInt | None): Optional manufacturing type ID
        type (str): Manufacturing category (window, door)

    Returns:
        HTMLResponse: Rendered HTML page

    Example:
        GET /api/v1/admin/entry/accessories?type=window
    """
    from app.core.manufacturing_type_resolver import ManufacturingTypeResolver
    from app.services.entry import JAVASCRIPT_CONDITION_EVALUATOR

    # If no manufacturing_type_id provided, resolve the default for accessories
    if manufacturing_type_id is None:
        default_type = await ManufacturingTypeResolver.get_default_for_page_type(
            db, "accessories", type
        )
        if default_type:
            manufacturing_type_id = default_type.id
        else:
            # No manufacturing types exist - show error page
            return templates.TemplateResponse(
                request,
                "admin/error.html.jinja",
                get_admin_context(
                    request,
                    current_superuser,
                    error_message=f"No manufacturing types found for {type} accessories. Please run the setup script.",
                    page_title="Setup Required",
                ),
                status_code=503,
            )

    return templates.TemplateResponse(
        request,
        "admin/entry/accessories.html.jinja",
        get_admin_context(
            request,
            current_superuser,
            active_page="entry_accessories",
            manufacturing_type_id=manufacturing_type_id,
            page_type="accessories",
            manufacturing_category=type,
            page_title=f"{type.title()} Accessories Entry",
            JAVASCRIPT_CONDITION_EVALUATOR=JAVASCRIPT_CONDITION_EVALUATOR,
            can_edit=True,  # TODO: Implement granular RBAC check
            can_delete=True,  # TODO: Implement granular RBAC check
        ),
    )


@router.get(
    "/glazing",
    response_class=HTMLResponse,
    summary="Admin Glazing Entry Page",
    description="Render the admin glazing data entry page",
    operation_id="adminGlazingEntryPage",
    responses={
        200: {
            "description": "Admin glazing entry page rendered successfully",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 403, 500),
    },
)
async def glazing_page(
    request: Request,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    manufacturing_type_id: Annotated[
        PositiveInt | None,
        Query(description="Manufacturing type ID for form generation"),
    ] = None,
    type: Annotated[
        str,
        Query(description="Manufacturing category: window, door"),
    ] = "window",
) -> HTMLResponse:
    """Render the admin glazing data entry page.

    Displays the glazing entry page with dynamic form generation
    and real-time preview capabilities within the admin interface.

    Args:
        request (Request): FastAPI request object
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session
        manufacturing_type_id (PositiveInt | None): Optional manufacturing type ID
        type (str): Manufacturing category (window, door)

    Returns:
        HTMLResponse: Rendered HTML page

    Example:
        GET /api/v1/admin/entry/glazing?type=window
    """
    from app.core.manufacturing_type_resolver import ManufacturingTypeResolver
    from app.services.entry import JAVASCRIPT_CONDITION_EVALUATOR

    # If no manufacturing_type_id provided, resolve the default for glazing
    if manufacturing_type_id is None:
        default_type = await ManufacturingTypeResolver.get_default_for_page_type(
            db, "glazing", type
        )
        if default_type:
            manufacturing_type_id = default_type.id
        else:
            # No manufacturing types exist - show error page
            return templates.TemplateResponse(
                request,
                "admin/error.html.jinja",
                get_admin_context(
                    request,
                    current_superuser,
                    error_message=f"No manufacturing types found for {type} glazing. Please run the setup script.",
                    page_title="Setup Required",
                ),
                status_code=503,
            )

    return templates.TemplateResponse(
        request,
        "admin/entry/glazing.html.jinja",
        get_admin_context(
            request,
            current_superuser,
            active_page="entry_glazing",
            manufacturing_type_id=manufacturing_type_id,
            page_type="glazing",
            manufacturing_category=type,
            page_title=f"{type.title()} Glazing Entry",
            JAVASCRIPT_CONDITION_EVALUATOR=JAVASCRIPT_CONDITION_EVALUATOR,
            can_edit=True,  # TODO: Implement granular RBAC check
            can_delete=True,  # TODO: Implement granular RBAC check
        ),
    )