"""Security utilities for authentication and authorization.

This module provides security functions for password hashing, JWT token
generation and validation using industry-standard libraries.

Public Functions:
    verify_password: Verify password against hash
    get_password_hash: Hash a plain text password
    create_access_token: Create JWT access token
    decode_access_token: Decode and verify JWT token

Features:
    - Bcrypt password hashing with passlib
    - JWT token generation and validation with python-jose
    - Configurable token expiration
    - Secure password verification
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import Field

from app.core.config import get_settings

__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.

    Args:
        plain_password (str): Plain text password
        hashed_password (str): Hashed password

    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.

    Args:
        password (str): Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: Annotated[str | Any, Field(description="Token subject (usually user ID)")],
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token.

    Args:
        subject (str | Any): Token subject (usually user ID)
        expires_delta (timedelta | None): Optional custom expiration time

    Returns:
        str: Encoded JWT token
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )

    to_encode = {"exp": expire, "sub": str(subject)}

    # Handle SecretStr for secret_key
    secret_key = (
        settings.security.secret_key.get_secret_value()
        if hasattr(settings.security.secret_key, "get_secret_value")
        else settings.security.secret_key
    )

    encoded_jwt = jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.security.algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> str | None:
    """Decode and verify JWT access token.

    Args:
        token (str): JWT token to decode

    Returns:
        str | None: Token subject if valid, None otherwise
    """
    settings = get_settings()

    # Handle SecretStr for secret_key
    secret_key = (
        settings.security.secret_key.get_secret_value()
        if hasattr(settings.security.secret_key, "get_secret_value")
        else settings.security.secret_key
    )

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.security.algorithm],
        )
        return payload.get("sub")
    except JWTError:
        return None
