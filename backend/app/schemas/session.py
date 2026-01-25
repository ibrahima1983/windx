"""Session Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for Session data validation,
serialization, and API request/response handling.

Public Classes:
    SessionBase: Base schema with common session attributes
    SessionCreate: Schema for creating new sessions
    Session: Schema for session API responses
    SessionInDB: Schema for session with token

Features:
    - Composed schemas for session management
    - Semantic types (PositiveInt)
    - IP address and user agent tracking
    - Expiration timestamp handling
    - Type-safe with Annotated types
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

__all__ = ["SessionBase", "SessionCreate", "Session", "SessionInDB"]


class SessionBase(BaseModel):
    """Base session schema with common attributes.

    Attributes:
        ip_address: Optional client IP address
        user_agent: Optional client user agent string
    """

    ip_address: Annotated[
        str | None,
        Field(
            default=None,
            max_length=45,
            description="IP address of the session",
            examples=["192.168.1.1"],
        ),
    ] = None
    user_agent: Annotated[
        str | None,
        Field(
            default=None,
            max_length=255,
            description="User agent string",
            examples=["Mozilla/5.0..."],
        ),
    ] = None


class SessionCreate(SessionBase):
    """Schema for creating a new session.

    Attributes:
        user_id: ID of the user this session belongs to
        token: JWT session token
        expires_at: Session expiration timestamp
    """

    user_id: Annotated[
        PositiveInt,
        Field(description="ID of the user this session belongs to"),
    ]
    token: Annotated[
        str,
        Field(
            min_length=1,
            description="Session token",
        ),
    ]
    expires_at: Annotated[
        datetime,
        Field(description="Session expiration timestamp"),
    ]


class Session(SessionBase):
    """Schema for session API response.

    Attributes:
        id: Session ID (positive integer)
        user_id: User ID
        is_active: Session active status
        expires_at: Session expiration timestamp
        created_at: Session creation timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Session ID"),
    ]
    user_id: Annotated[
        PositiveInt,
        Field(description="User ID"),
    ]
    is_active: Annotated[
        bool,
        Field(description="Whether session is active"),
    ]
    expires_at: Annotated[
        datetime,
        Field(description="Session expiration timestamp"),
    ]
    created_at: Annotated[
        datetime,
        Field(description="Session creation timestamp"),
    ]

    model_config = ConfigDict(from_attributes=True)


class SessionInDB(Session):
    """Schema for session in database (includes token).

    Attributes:
        token: JWT session token
    """

    token: Annotated[
        str,
        Field(description="Session token"),
    ]
