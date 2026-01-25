"""Authentication schemas.

This module defines Pydantic schemas for authentication operations
including login requests and token responses.

Public Classes:
    LoginRequest: Login request schema
    Token: Token response schema

Features:
    - Login credential validation
    - Token response formatting
    - Type-safe authentication data
"""

from typing import Annotated

from pydantic import BaseModel, Field

__all__ = ["LoginRequest", "Token"]


class LoginRequest(BaseModel):
    """Login request schema.

    Attributes:
        username: Username or email address
        password: User password
    """

    username: Annotated[
        str,
        Field(
            description="Username or email address",
            examples=["john_doe", "john@example.com"],
            min_length=3,
            max_length=255,
        ),
    ]
    password: Annotated[
        str,
        Field(
            description="User password",
            min_length=8,
            max_length=100,
        ),
    ]


class Token(BaseModel):
    """Token response schema.

    Attributes:
        access_token: JWT access token
        token_type: Token type (always "bearer")
    """

    access_token: Annotated[
        str,
        Field(
            description="JWT access token",
            examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
        ),
    ]
    token_type: Annotated[
        str,
        Field(
            description="Token type",
            examples=["bearer"],
            pattern="^bearer$",
        ),
    ] = "bearer"
