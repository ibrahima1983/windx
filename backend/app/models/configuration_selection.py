"""ConfigurationSelection model for individual attribute choices.

This module defines the ConfigurationSelection ORM model for storing
individual attribute selections within configurations using SQLAlchemy 2.0.

Public Classes:
    ConfigurationSelection: Individual attribute selection model

Features:
    - Flexible value storage (string, numeric, boolean, JSON)
    - Calculated impacts (price, weight, technical)
    - LTREE selection path for hierarchical context
    - Unique constraint per configuration and attribute
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import LTREE

if TYPE_CHECKING:
    from app.models.attribute_node import AttributeNode
    from app.models.configuration import Configuration

__all__ = ["ConfigurationSelection"]


class ConfigurationSelection(Base):
    """ConfigurationSelection model for individual attribute choices.

    Represents a single attribute selection within a configuration.
    Uses flexible value storage to accommodate different data types
    (string, numeric, boolean, JSON).

    Attributes:
        id: Primary key
        configuration_id: Foreign key to Configuration
        attribute_node_id: Foreign key to AttributeNode
        string_value: Text selections (materials, colors)
        numeric_value: Numerical inputs (dimensions, quantities)
        boolean_value: True/false choices (features)
        json_value: Complex structured data
        calculated_price_impact: Price effect of this selection
        calculated_weight_impact: Weight effect of this selection
        calculated_technical_impact: Technical effects (JSONB)
        selection_path: Hierarchical context (LTREE)
        created_at: Record creation timestamp
        configuration: Related configuration
        attribute_node: Related attribute node
    """

    __tablename__ = "configuration_selections"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )

    # Foreign keys
    configuration_id: Mapped[int] = mapped_column(
        ForeignKey("configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Configuration ID",
    )
    attribute_node_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_nodes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Attribute node ID",
    )

    # Flexible value storage (only one should be populated per row)
    string_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Text selections (materials, colors, etc.)",
    )
    numeric_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 6),
        nullable=True,
        default=None,
        doc="Numerical inputs (dimensions, quantities, etc.)",
    )
    boolean_value: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=None,
        doc="True/false choices (features enabled/disabled)",
    )
    json_value: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        doc="Complex structured data (multiple properties)",
    )

    # Calculated impacts (updated by triggers or application)
    calculated_price_impact: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        default=None,
        doc="Price effect of this selection",
    )
    calculated_weight_impact: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        default=None,
        doc="Weight effect of this selection",
    )
    calculated_technical_impact: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        doc="Technical effects (JSONB)",
    )

    # Hierarchy context
    selection_path: Mapped[str] = mapped_column(
        LTREE,
        nullable=False,
        doc="Hierarchical path for context (LTREE)",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp (UTC)",
    )

    # Relationships
    configuration: Mapped[Configuration] = relationship(
        "Configuration",
        back_populates="selections",
    )
    attribute_node: Mapped[AttributeNode] = relationship(
        "AttributeNode",
    )

    # Constraints and Indexes
    __table_args__ = (
        # Unique constraint: one selection per attribute per configuration
        UniqueConstraint(
            "configuration_id",
            "attribute_node_id",
            name="uq_config_attr",
        ),
        # Composite index for filtering by configuration
        Index(
            "idx_config_selections_config",
            "configuration_id",
        ),
        # Composite index for filtering by attribute node
        Index(
            "idx_config_selections_attr",
            "attribute_node_id",
        ),
        # GiST index on selection_path for hierarchical queries
        Index(
            "idx_config_selections_path",
            "selection_path",
            postgresql_using="gist",
        ),
        # GIN index on json_value for JSONB queries
        Index(
            "idx_config_selections_json",
            "json_value",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation of ConfigurationSelection.

        Returns:
            str: ConfigurationSelection representation with IDs and value
        """
        value = self.string_value or self.numeric_value or self.boolean_value or self.json_value
        return (
            f"<ConfigurationSelection(id={self.id}, "
            f"config_id={self.configuration_id}, "
            f"attr_id={self.attribute_node_id}, "
            f"value={value})>"
        )
