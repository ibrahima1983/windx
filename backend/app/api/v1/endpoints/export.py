"""Data export endpoints.

This module provides endpoints for exporting user data in various formats
including JSON and CSV.

Public Variables:
    router: FastAPI router for export endpoints

Features:
    - Export user data to JSON
    - Export user data to CSV
    - Streaming responses for large datasets
    - Permission-based access control
"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.types import CurrentSuperuser, CurrentUser, DBSession
from app.schemas.responses import get_common_responses
from app.services.user import UserService

__all__ = ["router"]

router = APIRouter(
    tags=["Export"],
    responses=get_common_responses(401, 403, 500),
)


@router.get(
    "/my-data",
    summary="Export My Data",
    description="Export the authenticated user's data in JSON format (GDPR compliance).",
    response_description="User data in JSON format",
    operation_id="exportMyData",
    responses={
        200: {
            "description": "Successfully exported user data",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "username": "john_doe",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_superuser": False,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                }
            },
        },
        **get_common_responses(401, 500),
    },
)
async def export_my_data(
    current_user: CurrentUser,
) -> dict:
    """Export authenticated user's data.

    GDPR compliance: Users can export their personal data.

    Args:
        current_user (User): Current authenticated user

    Returns:
        dict: User data in JSON format
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat(),
    }


@router.get(
    "/users/json",
    summary="Export All Users (JSON)",
    description="Export all users data in JSON format (superuser only).",
    response_description="All users data in JSON format",
    operation_id="exportUsersJson",
    responses={
        200: {
            "description": "Successfully exported users data",
            "content": {
                "application/json": {
                    "example": {
                        "exported_at": "2024-01-01T00:00:00Z",
                        "total_users": 2,
                        "users": [
                            {
                                "id": 1,
                                "email": "user1@example.com",
                                "username": "user1",
                                "full_name": "User One",
                                "is_active": True,
                                "created_at": "2024-01-01T00:00:00Z",
                            }
                        ],
                    }
                }
            },
        },
        **get_common_responses(401, 403, 500),
    },
)
async def export_users_json(
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> dict:
    """Export all users data in JSON format.

    Superuser only. Exports all users with their basic information.

    Args:
        current_superuser (User): Current superuser
        db (AsyncSession): Database session

    Returns:
        dict: All users data in JSON format
    """
    user_service = UserService(db)
    users = await user_service.list_users()

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "total_users": len(users),
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }
            for user in users
        ],
    }


@router.get(
    "/users/csv",
    summary="Export All Users (CSV)",
    description="Export all users data in CSV format (superuser only).",
    response_description="All users data in CSV format",
    operation_id="exportUsersCsv",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Successfully exported users data as CSV",
            "content": {
                "text/csv": {
                    "example": "id,email,username,full_name,is_active,is_superuser,created_at,updated_at\n1,user@example.com,john_doe,John Doe,true,false,2024-01-01T00:00:00Z,2024-01-01T00:00:00Z\n"
                }
            },
        },
        **get_common_responses(401, 403, 500),
    },
)
async def export_users_csv(
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> StreamingResponse:
    """Export all users data in CSV format.

    Superuser only. Exports all users as a downloadable CSV file.

    Args:
        current_superuser (User): Current superuser
        db (AsyncSession): Database session

    Returns:
        StreamingResponse: CSV file download
    """
    user_service = UserService(db)
    users = await user_service.list_users()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "id",
            "email",
            "username",
            "full_name",
            "is_active",
            "is_superuser",
            "created_at",
            "updated_at",
        ]
    )

    # Write data
    for user in users:
        writer.writerow(
            [
                user.id,
                user.email,
                user.username,
                user.full_name or "",
                user.is_active,
                user.is_superuser,
                user.created_at.isoformat(),
                user.updated_at.isoformat(),
            ]
        )

    # Get CSV content
    output.seek(0)
    csv_content = output.getvalue()

    # Create streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=users_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )
