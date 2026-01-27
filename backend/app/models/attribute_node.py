"""AttributeNode model for hierarchical product configuration system."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

# Avoid circular import - use TYPE_CHECKING for type hints
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import LTREE

if TYPE_CHECKING:
    from app.models.manufacturing_type import ManufacturingType


class AttributeNode(Base):
    """
    Hierarchical attribute tree node with LTREE for efficient traversal.

    Represents configurable product attributes in a tree structure.
    Uses PostgreSQL LTREE extension for fast hierarchical queries.

    Node Types:
        - category: Organizational grouping (e.g., "Frame Options")
        - attribute: Configurable property (e.g., "Frame Material")
        - option: Selectable choice (e.g., "Aluminum", "Vinyl")
        - component: Physical component (e.g., "Handle", "Lock")
        - technical_spec: Technical property (e.g., "U-Value", "Load Capacity")

    Data Types:
        - string: Text values (colors, materials)
        - number: Numeric values (dimensions, quantities)
        - boolean: Yes/no choices (features)
        - formula: Calculated values (area, volume)
        - dimension: Size measurements (width, height)
        - selection: Choice from options

    Price Impact Types:
        - fixed: Add/subtract fixed amount (+$50)
        - percentage: Multiply by percentage (+15%)
        - formula: Calculate dynamically (area * price_per_sqft)
    """

    __tablename__ = "attribute_nodes"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Foreign keys
    manufacturing_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("manufacturing_types.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    parent_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("attribute_nodes.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )

    # Page type for multi-page architecture
    page_type: Mapped[str] = mapped_column(
        String(20),
        default="profile",
        nullable=False,
        comment="Page type: profile, accessories, glazing",
    )

    # Basic information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Human-readable display name. If null, auto-generated from 'name' field using title case conversion.",
    )
    node_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type: category, attribute, option, component, technical_spec",
    )
    data_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Data type: string, number, boolean, formula, dimension, selection",
    )

    # Dynamic behavior
    display_condition: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Conditional display logic (when to show this node)",
    )
    validation_rules: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Input validation rules",
    )
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Pricing impacts
    price_impact_type: Mapped[str] = mapped_column(
        String(20),
        default="fixed",
        nullable=False,
        comment="How it affects price: fixed, percentage, formula",
    )
    price_impact_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Fixed price adjustment amount",
    )
    price_formula: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Dynamic price calculation formula",
    )

    # Weight impacts
    weight_impact: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Fixed weight addition in kg",
    )
    weight_formula: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Dynamic weight calculation formula",
    )

    # Technical properties
    technical_property_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Type of technical property (u_value, load_capacity, etc.)",
    )
    technical_impact_formula: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Technical calculation formula",
    )

    # Calculated field metadata
    calculated_field: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Calculation metadata for auto-calculated fields (type, operands, trigger_on, precision)",
    )

    # Hierarchy (LTREE for fast queries)
    ltree_path: Mapped[str] = mapped_column(
        LTREE,
        nullable=False,
        comment="Hierarchical path for efficient tree traversal",
    )
    depth: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Nesting level in the tree",
    )

    # UI configuration
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order among siblings",
    )
    ui_component: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="UI control type (dropdown, slider, input, etc.)",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Help text for users",
    )
    help_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional guidance for users",
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Image/logo URL for the entity (used in Relations management)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    manufacturing_type: Mapped[ManufacturingType | None] = relationship(
        "ManufacturingType",
        back_populates="attribute_nodes",
    )
    parent: Mapped[AttributeNode | None] = relationship(
        "AttributeNode",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_node_id],
    )
    children: Mapped[list[AttributeNode]] = relationship(
        "AttributeNode",
        back_populates="parent",
        foreign_keys=[parent_node_id],
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        # GiST index on ltree_path for efficient hierarchical queries
        Index(
            "idx_attribute_nodes_ltree_path",
            "ltree_path",
            postgresql_using="gist",
        ),
        # Composite index for filtering by manufacturing type, page type, and node type
        Index(
            "idx_attribute_nodes_mfg_page_node_type",
            "manufacturing_type_id",
            "page_type",
            "node_type",
        ),
        # Composite index for filtering by manufacturing type and node type (backward compatibility)
        Index(
            "idx_attribute_nodes_mfg_type_node_type",
            "manufacturing_type_id",
            "node_type",
        ),
        # Partial index for technical properties
        Index(
            "idx_attribute_nodes_technical_property",
            "technical_property_type",
            postgresql_where=text("technical_property_type IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        """String representation of AttributeNode."""
        return (
            f"<AttributeNode(id={self.id}, name='{self.name}', "
            f"node_type='{self.node_type}', path='{self.ltree_path}')>"
        )

    def get_display_name(self) -> str:
        """
        Get the display name for this attribute node.
        
        Returns the stored display_name if available, otherwise generates one from the name field.
        
        Generation Rules:
        - Converts snake_case and kebab-case to Title Case
        - Replaces underscores and hyphens with spaces
        - Preserves parentheses and their content
        - Capitalizes each word appropriately
        
        Examples:
            - "opening_system" → "Opening System"
            - "price-per-meter" → "Price Per Meter"  
            - "width_(mm)" → "Width (mm)"
            - "u_value" → "U Value"
            - "built-in_flyscreen_track" → "Built In Flyscreen Track"
        
        Returns:
            str: Human-readable display name for UI presentation
        """
        if self.display_name:
            return self.display_name
            
        return self._generate_display_name_from_name(self.name)
    
    @staticmethod
    def _generate_display_name_from_name(name: str) -> str:
        """
        Generate a human-readable display name from a technical field name.
        
        This method converts technical field names (typically in snake_case or kebab-case)
        into user-friendly display names suitable for UI presentation.
        
        Conversion Rules:
        1. Replace underscores (_) and hyphens (-) with spaces
        2. Convert to Title Case (capitalize first letter of each word)
        3. Preserve parentheses and their content as-is
        4. Handle special cases for common abbreviations
        
        Args:
            name (str): Technical field name (e.g., "opening_system", "price-per-meter")
            
        Returns:
            str: Human-readable display name (e.g., "Opening System", "Price Per Meter")
            
        Examples:
            >>> AttributeNode._generate_display_name_from_name("opening_system")
            "Opening System"
            >>> AttributeNode._generate_display_name_from_name("price-per-meter")
            "Price Per Meter"
            >>> AttributeNode._generate_display_name_from_name("width_(mm)")
            "Width (mm)"
            >>> AttributeNode._generate_display_name_from_name("built-in_flyscreen_track")
            "Built In Flyscreen Track"
            >>> AttributeNode._generate_display_name_from_name("u_value")
            "U Value"
        """
        if not name:
            return ""
            
        # Replace underscores and hyphens with spaces
        display_name = name.replace("_", " ").replace("-", " ")
        
        # Convert to title case
        display_name = display_name.title()
        
        return display_name
