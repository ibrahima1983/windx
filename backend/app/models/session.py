"""Session database model.

This module defines the Session ORM model for tracking user authentication
sessions with token management and expiration.

Public Classes:
    Session: Session model for user authentication tracking

Features:
    - JWT token storage and validation
    - Session expiration management
    - IP address and user agent tracking
    - Active/inactive status control
    - Foreign key relationship with User model
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User

__all__ = ["Session"]


class Session(Base):
    """Session model for tracking user sessions.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        token: JWT access token (unique)
        ip_address: Optional client IP address
        user_agent: Optional client user agent string
        is_active: Session active status
        expires_at: Session expiration timestamp
        created_at: Session creation timestamp
        user: Related User record
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to users table",
    )
    token: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        index=True,
        nullable=False,
        doc="JWT access token (unique)",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        default=None,
        doc="Client IP address (IPv4 or IPv6)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        doc="Client user agent string",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,  # Index for filtering active sessions
        doc="Session active status",
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,  # Index for expiration queries
        doc="Session expiration timestamp (UTC)",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,  # Index for sorting by creation date
        doc="Session creation timestamp (UTC)",
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        """String representation of Session.

        Returns:
            str: Session representation with ID, user ID, and active status
        """
        return f"<Session(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
