"""User database model.

This module defines the User ORM model for authentication and user management
using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    User: User model with authentication fields and relationships

Features:
    - Email and username uniqueness constraints
    - Password hashing support
    - Active/superuser status flags
    - Automatic timestamp management
    - One-to-many relationship with sessions
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.session import Session

__all__ = ["User"]


class User(Base):
    """User model for authentication and user management.

    Attributes:
        id: Primary key
        email: Unique email address
        username: Unique username
        hashed_password: Bcrypt hashed password
        full_name: Optional full name
        is_active: Account active status
        is_superuser: Superuser privileges flag
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        sessions: Related session records
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,  # Ensure ID appears first in queries
        doc="Primary key identifier",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="User email address (unique)",
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        doc="Username (unique, 3-50 characters)",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password",
    )
    full_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        doc="User's full name (optional)",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,  # Index for filtering active users
        doc="Account active status",
    )
    is_superuser: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,  # Index for filtering superusers
        doc="Superuser privileges flag",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="customer",
        nullable=False,
        index=True,  # Index for role-based filtering
        doc="User role for RBAC (customer, salesman, data_entry, partner, superadmin)",
    )

    def __init__(self, **kwargs):
        """Initialize User with default role if not provided."""
        if "role" not in kwargs:
            # Set role based on is_superuser flag
            if kwargs.get("is_superuser", False):
                kwargs["role"] = "superadmin"
            else:
                kwargs["role"] = "customer"
        super().__init__(**kwargs)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,  # Index for sorting by creation date
        doc="Account creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        doc="Last update timestamp (UTC)",
    )

    # Relationships
    sessions: Mapped[list[Session]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def has_role(self, role: str) -> bool:
        """Check if user has specific role.

        Args:
            role: Role to check (string value from Role enum)

        Returns:
            True if user has the role or is superadmin, False otherwise
        """
        return self.role == role or self.role == "superadmin"

    def __repr__(self) -> str:
        """String representation of User.

        Returns:
            str: User representation with ID, email, and username
        """
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
