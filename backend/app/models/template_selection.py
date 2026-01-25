"""Template Selection model for pre-selected attributes in templates.

This module defines the TemplateSelection ORM model for storing
pre-selected attribute choices within configuration templates
using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    TemplateSelection: Pre-selected attribute in a template

Features:
    - Flexible value storage (string, numeric, boolean, JSON)
    - LTREE path for hierarchical context
    - Cascade delete with template
    - Unique constraint per template and attribute
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
    from app.models.configuration_template import ConfigurationTemplate

__all__ = ["TemplateSelection"]


class TemplateSelection(Base):
    """Template Selection model for pre-selected attributes.

    Represents individual attribute choices within a configuration template.
    When a template is applied, these selections are copied to create
    a new configuration.

    Attributes:
        id: Primary key
        template_id: Foreign key to ConfigurationTemplate
        attribute_node_id: Foreign key to AttributeNode
        string_value: Text value for string attributes
        numeric_value: Numeric value for number attributes
        boolean_value: Boolean value for yes/no attributes
        json_value: Complex structured data for JSON attributes
        selection_path: LTREE path for hierarchical context
        created_at: Record creation timestamp
        template: Related configuration template
        attribute_node: Related attribute node
    """

    __tablename__ = "template_selections"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )

    # Foreign keys
    template_id: Mapped[int] = mapped_column(
        ForeignKey("configuration_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Configuration template ID",
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
        doc="Text value for string attributes",
    )
    numeric_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 6),
        nullable=True,
        default=None,
        doc="Numeric value for number attributes",
    )
    boolean_value: Mapped[bool | None] = mapped_column(
        nullable=True,
        default=None,
        doc="Boolean value for yes/no attributes",
    )
    json_value: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        doc="Complex structured data for JSON attributes",
    )

    # Hierarchy context (LTREE for efficient path queries)
    selection_path: Mapped[str] = mapped_column(
        LTREE,
        nullable=False,
        index=True,
        doc="Hierarchical path for context (LTREE)",
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

    # Relationships
    template: Mapped[ConfigurationTemplate] = relationship(
        "ConfigurationTemplate",
        back_populates="selections",
        doc="Related configuration template",
    )
    attribute_node: Mapped[AttributeNode] = relationship(
        "AttributeNode",
        doc="Related attribute node",
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint: one selection per attribute per template
        UniqueConstraint(
            "template_id",
            "attribute_node_id",
            name="uq_template_attr",
        ),
        # Composite index for filtering by template
        Index(
            "idx_template_selections_template",
            "template_id",
        ),
        # Composite index for filtering by attribute node
        Index(
            "idx_template_selections_attr_node",
            "attribute_node_id",
        ),
        # GIST index on selection_path for LTREE queries
        Index(
            "idx_template_selections_path",
            "selection_path",
            postgresql_using="gist",
        ),
    )

    def __repr__(self) -> str:
        """String representation of TemplateSelection.

        Returns:
            str: Selection representation with ID and template ID
        """
        value = self.string_value or self.numeric_value or self.boolean_value or self.json_value
        return (
            f"<TemplateSelection(id={self.id}, template_id={self.template_id}, "
            f"attribute_node_id={self.attribute_node_id}, value={value})>"
        )
