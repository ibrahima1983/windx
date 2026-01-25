"""ManufacturingType database model.

This module defines the ManufacturingType ORM model for product categories
using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    ManufacturingType: Product category model (Window, Door, Table)

Features:
    - Unique product category names
    - Base pricing and weight
    - Active/inactive status
    - Automatic timestamp management
    - Relationships with attribute nodes and configurations
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.attribute_node import AttributeNode
    from app.models.configuration import Configuration
    from app.models.configuration_template import ConfigurationTemplate

__all__ = ["ManufacturingType"]


class ManufacturingType(Base):
    """ManufacturingType model for product categories.

    Represents product categories like Window, Door, Table, etc.
    Each manufacturing type has its own attribute hierarchy and base pricing.

    Attributes:
        id: Primary key
        name: Unique product category name
        description: Detailed description of the product type
        base_category: High-level grouping (window, door, furniture)
        image_url: URL to product category image
        base_price: Starting price for this product type
        base_weight: Base weight in kg
        is_active: Whether this product type is available
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        attribute_nodes: Related attribute hierarchy
        configurations: Related customer configurations
        templates: Related configuration templates
    """

    __tablename__ = "manufacturing_types"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique product category name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Detailed description of the product type",
    )
    base_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        index=True,
        doc="High-level grouping (window, door, furniture)",
    )
    image_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        doc="URL to product category image",
    )
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Starting price for this product type",
    )
    base_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Base weight in kg",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        doc="Whether this product type is available",
    )
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
    attribute_nodes: Mapped[list[AttributeNode]] = relationship(
        "AttributeNode",
        back_populates="manufacturing_type",
        cascade="all, delete-orphan",
    )
    configurations: Mapped[list[Configuration]] = relationship(
        "Configuration",
        back_populates="manufacturing_type",
    )
    templates: Mapped[list[ConfigurationTemplate]] = relationship(
        "ConfigurationTemplate",
        back_populates="manufacturing_type",
    )

    def __repr__(self) -> str:
        """String representation of ManufacturingType.

        Returns:
            str: ManufacturingType representation with ID and name
        """
        return f"<ManufacturingType(id={self.id}, name={self.name})>"
