"""User Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for User data validation,
serialization, and API request/response handling.

Public Classes:
    UserBase: Base schema with common user attributes
    UserCreate: Schema for user registration
    UserUpdate: Schema for user updates (partial)
    User: Schema for user API responses
    UserInDB: Schema for user with hashed password

Features:
    - Composed schemas (not monolithic)
    - Semantic types (EmailStr, PositiveInt)
    - Field validation with regex patterns
    - Type-safe with Annotated types
    - Automatic ORM conversion support
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt

__all__ = ["UserBase", "UserCreate", "UserUpdate", "User", "UserInDB"]


class UserBase(BaseModel):
    """Base user schema with common attributes.

    Attributes:
        email: User email address (validated)
        username: Unique username (alphanumeric, dash, underscore)
        full_name: Optional full name
    """

    email: Annotated[
        EmailStr,
        Field(
            description="User email address",
            examples=["user@example.com"],
        ),
    ]
    username: Annotated[
        str,
        Field(
            min_length=3,
            max_length=50,
            pattern="^[a-zA-Z0-9_-]+$",
            description="Unique username",
            examples=["john_doe"],
        ),
    ]
    full_name: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="User's full name",
            examples=["John Doe"],
        ),
    ] = None
    role: Annotated[
        str,
        Field(
            default="customer",
            max_length=50,
            description="User role for RBAC",
            examples=["customer", "salesman", "data_entry", "partner", "superadmin"],
        ),
    ] = "customer"


class UserCreate(UserBase):
    """Schema for creating a new user.

    Attributes:
        password: Plain text password (min 8 chars)
    """

    password: Annotated[
        str,
        Field(
            min_length=8,
            max_length=100,
            description="User password",
            examples=["SecurePass123!"],
        ),
    ]


class UserUpdate(BaseModel):
    """Schema for updating user information.

    All fields are optional for partial updates.

    Attributes:
        email: Optional new email address
        username: Optional new username
        full_name: Optional new full name
        password: Optional new password
        is_active: Optional active status update
    """

    email: Annotated[
        EmailStr | None,
        Field(
            default=None,
            description="User email address",
        ),
    ] = None
    username: Annotated[
        str | None,
        Field(
            default=None,
            min_length=3,
            max_length=50,
            pattern="^[a-zA-Z0-9_-]+$",
            description="Unique username",
        ),
    ] = None
    full_name: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="User's full name",
        ),
    ] = None
    password: Annotated[
        str | None,
        Field(
            default=None,
            min_length=8,
            max_length=100,
            description="User password",
        ),
    ] = None
    is_active: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether user account is active",
        ),
    ] = None
    role: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="User role for RBAC",
        ),
    ] = None


class User(UserBase):
    """Schema for user API response.

    Attributes:
        id: User ID (positive integer)
        is_active: Account active status
        is_superuser: Superuser privileges flag
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="User ID"),
    ]
    is_active: Annotated[
        bool,
        Field(description="Whether user account is active"),
    ]
    is_superuser: Annotated[
        bool,
        Field(description="Whether user has superuser privileges"),
    ]
    created_at: Annotated[
        datetime,
        Field(description="Account creation timestamp"),
    ]
    updated_at: Annotated[
        datetime,
        Field(description="Last update timestamp"),
    ]
    role: Annotated[
        str,
        Field(description="User role for RBAC"),
    ]

    model_config = ConfigDict(from_attributes=True)


class UserInDB(User):
    """Schema for user in database (includes hashed password).

    Attributes:
        hashed_password: Bcrypt hashed password
    """

    hashed_password: Annotated[
        str,
        Field(description="Hashed password"),
    ]
