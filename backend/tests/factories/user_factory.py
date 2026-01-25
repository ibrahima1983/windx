"""User factory for test data generation.

This module provides factory functions for creating user test data
with realistic values and proper validation.

Public Functions:
    create_user_data: Create user data dictionary
    create_user_create_schema: Create UserCreate schema
    create_multiple_users_data: Create multiple user data dictionaries

Features:
    - Realistic test data
    - Unique values per call
    - Customizable fields
    - Proper validation
"""

from __future__ import annotations

import uuid
from typing import Any

from app.schemas.user import UserCreate

__all__ = [
    "create_user_data",
    "create_user_create_schema",
    "create_multiple_users_data",
]


def reset_counter() -> None:
    """Reset the global counter for test isolation.

    Note: This function is kept for compatibility but is no longer needed
    since we use UUIDs for uniqueness.
    """
    pass  # No-op since we use UUIDs now


def _get_unique_id() -> str:
    """Get unique ID for test data.

    Returns:
        str: Unique UUID-based identifier
    """
    return str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for readability


def create_user_data(
    email: str | None = None,
    username: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create user data dictionary.

    Args:
        email (str | None): User email (auto-generated if None)
        username (str | None): Username (auto-generated if None)
        password (str | None): Password (default if None)
        full_name (str | None): Full name (auto-generated if None)
        is_active (bool): Active status
        is_superuser (bool): Superuser status
        **kwargs: Additional fields

    Returns:
        dict[str, Any]: User data dictionary
    """
    unique_id = _get_unique_id()

    data = {
        "email": email or f"user{unique_id}@example.com",
        "username": username or f"user{unique_id}",
        "password": password or "FactoryPassword123!",  # Secure default for factory-created users
        "full_name": full_name or f"Test User {unique_id}",
        "is_active": is_active,
        "is_superuser": is_superuser,
    }

    data.update(kwargs)
    return data


def create_user_create_schema(
    email: str | None = None,
    username: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
    **kwargs: Any,
) -> UserCreate:
    """Create UserCreate schema.

    Args:
        email (str | None): User email (auto-generated if None)
        username (str | None): Username (auto-generated if None)
        password (str | None): Password (default if None)
        full_name (str | None): Full name (auto-generated if None)
        **kwargs: Additional fields

    Returns:
        UserCreate: User creation schema
    """
    data = create_user_data(
        email=email,
        username=username,
        password=password,
        full_name=full_name,
        **kwargs,
    )
    # Remove fields not in UserCreate
    data.pop("is_active", None)
    data.pop("is_superuser", None)

    return UserCreate(**data)


def create_multiple_users_data(count: int = 3) -> list[dict[str, Any]]:
    """Create multiple user data dictionaries.

    Args:
        count (int): Number of users to create

    Returns:
        list[dict[str, Any]]: List of user data dictionaries
    """
    return [create_user_data() for _ in range(count)]
