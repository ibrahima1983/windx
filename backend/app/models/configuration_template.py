"""Configuration Template model for pre-defined configurations.

This module defines the ConfigurationTemplate ORM model for managing
reusable product configuration templates using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    ConfigurationTemplate: Pre-defined configuration template model

Features:
    - Template type classification (standard, premium, economy, custom)
    - Public/private visibility control
    - Usage tracking and success metrics
    - Estimated pricing and weight
    - Relationships with manufacturing types, users, and selections
    - Automatic timestamp management
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.manufacturing_type import ManufacturingType
    from app.models.template_selection import TemplateSelection
    from app.models.user import User

__all__ = ["ConfigurationTemplate"]


class ConfigurationTemplate(Base):
    """Configuration Template model for pre-defined configurations.

    Represents reusable product configuration templates that can be
    applied to create new configurations quickly. Templates track
    usage metrics and success rates.

    Attributes:
        id: Primary key
        name: Template name
        description: Template description
        manufacturing_type_id: Foreign key to ManufacturingType
        template_type: Type classification (standard, premium, economy, custom)
        is_public: Customer visibility flag
        usage_count: Number of times template was used
        success_rate: Conversion rate to orders (percentage)
        estimated_price: Quick reference price
        estimated_weight: Quick reference weight
        created_by: Foreign key to User (creator)
        is_active: Active status
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        manufacturing_type: Related manufacturing type
        selections: Related template selections
        creator: User who created the template
    """

    __tablename__ = "configuration_templates"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        doc="Template name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Template description",
    )

    # Foreign keys
    manufacturing_type_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturing_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Manufacturing type ID",
    )

    # Template classification
    template_type: Mapped[str] = mapped_column(
        String(50),
        default="standard",
        nullable=False,
        index=True,
        doc="Type: standard, premium, economy, custom",
    )

    # Visibility and status
    is_public: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        doc="Customer visibility flag",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        doc="Active status",
    )

    # Usage metrics
    usage_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        doc="Number of times template was used",
    )
    success_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Conversion rate to orders (percentage)",
    )

    # Estimated values for quick reference
    estimated_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Quick reference price",
    )
    estimated_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Quick reference weight in kg",
    )

    # Creator tracking
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User ID of template creator",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Record creation timestamp (UTC)",
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
    manufacturing_type: Mapped[ManufacturingType] = relationship(
        "ManufacturingType",
        back_populates="templates",
        doc="Related manufacturing type",
    )
    selections: Mapped[list[TemplateSelection]] = relationship(
        "TemplateSelection",
        back_populates="template",
        cascade="all, delete-orphan",
        doc="Related template selections",
    )
    creator: Mapped[User | None] = relationship(
        "User",
        doc="User who created the template",
    )

    # Indexes
    __table_args__ = (
        # Composite index for filtering by manufacturing type and template type
        Index(
            "idx_templates_mfg_type_template_type",
            "manufacturing_type_id",
            "template_type",
        ),
        # Composite index for filtering by public and active status
        Index(
            "idx_templates_public_active",
            "is_public",
            "is_active",
        ),
        # Partial index for public templates only
        Index(
            "idx_templates_public_only",
            "is_public",
            postgresql_where="is_public = true",
        ),
        # Partial index for active templates only
        Index(
            "idx_templates_active_only",
            "is_active",
            postgresql_where="is_active = true",
        ),
    )

    def __repr__(self) -> str:
        """String representation of ConfigurationTemplate.

        Returns:
            str: Template representation with ID and name
        """
        return (
            f"<ConfigurationTemplate(id={self.id}, name='{self.name}', "
            f"type='{self.template_type}', usage_count={self.usage_count})>"
        )
