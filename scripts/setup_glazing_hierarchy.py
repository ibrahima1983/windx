#!/usr/bin/env python3
"""Setup script for Window Glazing Entry manufacturing type and attribute hierarchy.

This script creates attribute nodes for window glazing based on the business
requirements from the reference documents (glass specs, thickness, treatments).

Usage:
    python setup_glazing_hierarchy.py
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_engine, get_session_maker
from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType


async def get_or_create_manufacturing_type(session: AsyncSession) -> ManufacturingType:
    """Get or create Window Profile Entry manufacturing type."""
    print("Getting Window Profile Entry manufacturing type...")

    # Check if it already exists
    stmt = select(ManufacturingType).where(ManufacturingType.name == "Window Profile Entry")
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        print(f"  ✅ Using existing manufacturing type (ID: {existing.id})")
        return existing

    # Create new manufacturing type if it doesn't exist
    manufacturing_type = ManufacturingType(
        name="Window Profile Entry",
        description="Window profile data entry system for comprehensive product configuration",
        base_category="window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
        is_active=True,
    )

    session.add(manufacturing_type)
    await session.commit()
    await session.refresh(manufacturing_type)

    print(f"  ✅ Created manufacturing type (ID: {manufacturing_type.id})")
    return manufacturing_type


async def create_glazing_attribute_nodes(
    session: AsyncSession, manufacturing_type: ManufacturingType
) -> None:
    """Create glazing attribute nodes based on business requirements."""
    print("Creating glazing attribute nodes...")

    # Check if glazing nodes already exist
    stmt = select(AttributeNode).where(
        AttributeNode.manufacturing_type_id == manufacturing_type.id,
        AttributeNode.page_type == "glazing",
    )
    result = await session.execute(stmt)
    existing_nodes = result.scalars().all()

    if existing_nodes:
        print(f"  ⚠️  Found {len(existing_nodes)} existing glazing nodes, skipping creation")
        return

    # Define glazing attribute nodes based on reference documents
    glazing_definitions = [
        # Basic Glass Information
        {
            "name": "glass_type",
            "description": "Type of glass",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "glazing.basic.glass_type",
            "depth": 2,
            "sort_order": 1,
            "ui_component": "dropdown",
            "help_text": "Select the type of glass",
            "validation_rules": {
                "options": [
                    "Clear",
                    "Tinted",
                    "Reflective",
                    "Low-E",
                    "Laminated",
                    "Tempered",
                    "Insulated",
                    "Acoustic",
                    "Security",
                    "Other",
                ]
            },
        },
        {
            "name": "glass_thickness",
            "description": "Glass thickness (mm)",
            "node_type": "attribute",
            "data_type": "number",
            "required": True,
            "ltree_path": "glazing.basic.glass_thickness",
            "depth": 2,
            "sort_order": 2,
            "ui_component": "dropdown",
            "help_text": "Select glass thickness in millimeters",
            "validation_rules": {"options": ["4", "5", "6", "8", "10", "12", "15", "19", "25"]},
        },
        {
            "name": "pane_configuration",
            "description": "Pane configuration",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "glazing.basic.pane_configuration",
            "depth": 2,
            "sort_order": 3,
            "ui_component": "dropdown",
            "help_text": "Select the pane configuration",
            "validation_rules": {
                "options": ["Single Pane", "Double Pane", "Triple Pane", "Quadruple Pane"]
            },
        },
        {
            "name": "air_gap",
            "description": "Air gap between panes (mm)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.basic.air_gap",
            "depth": 2,
            "sort_order": 4,
            "ui_component": "number",
            "help_text": "Air gap between glass panes in mm",
            "validation_rules": {"min": 6, "max": 20},
            "display_condition": {
                "operator": "not_equals",
                "field": "pane_configuration",
                "value": "Single Pane",
            },
        },
        # Glass Treatments and Coatings
        {
            "name": "low_e_coating",
            "description": "Low-E coating",
            "node_type": "attribute",
            "data_type": "boolean",
            "required": False,
            "ltree_path": "glazing.treatments.low_e_coating",
            "depth": 2,
            "sort_order": 5,
            "ui_component": "checkbox",
            "help_text": "Check if glass has Low-E coating for energy efficiency",
        },
        {
            "name": "coating_position",
            "description": "Coating position",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "glazing.treatments.coating_position",
            "depth": 2,
            "sort_order": 6,
            "ui_component": "dropdown",
            "help_text": "Position of the coating on the glass",
            "validation_rules": {
                "options": [
                    "Surface 1 (Outside)",
                    "Surface 2 (Inside outer pane)",
                    "Surface 3 (Outside inner pane)",
                    "Surface 4 (Inside)",
                ]
            },
            "display_condition": {"operator": "equals", "field": "low_e_coating", "value": True},
        },
        {
            "name": "tint_color",
            "description": "Tint color",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "glazing.treatments.tint_color",
            "depth": 2,
            "sort_order": 7,
            "ui_component": "dropdown",
            "help_text": "Select tint color if applicable",
            "validation_rules": {
                "options": ["None", "Bronze", "Gray", "Green", "Blue", "Silver", "Gold", "Other"]
            },
        },
        {
            "name": "uv_protection",
            "description": "UV protection level (%)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.treatments.uv_protection",
            "depth": 2,
            "sort_order": 8,
            "ui_component": "number",
            "help_text": "UV protection percentage (0-100%)",
            "validation_rules": {"min": 0, "max": 100},
        },
        # Performance Specifications
        {
            "name": "u_value",
            "description": "U-Value (W/m²K)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.performance.u_value",
            "depth": 2,
            "sort_order": 9,
            "ui_component": "number",
            "help_text": "Thermal transmittance (lower is better for insulation)",
            "validation_rules": {"min": 0.1, "max": 6.0},
        },
        {
            "name": "shgc",
            "description": "Solar Heat Gain Coefficient",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.performance.shgc",
            "depth": 2,
            "sort_order": 10,
            "ui_component": "number",
            "help_text": "Solar heat gain coefficient (0-1, lower blocks more heat)",
            "validation_rules": {"min": 0.0, "max": 1.0},
        },
        {
            "name": "visible_transmittance",
            "description": "Visible Light Transmittance (%)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.performance.visible_transmittance",
            "depth": 2,
            "sort_order": 11,
            "ui_component": "number",
            "help_text": "Percentage of visible light transmitted (0-100%)",
            "validation_rules": {"min": 0, "max": 100},
        },
        {
            "name": "sound_reduction",
            "description": "Sound Reduction (dB)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.performance.sound_reduction",
            "depth": 2,
            "sort_order": 12,
            "ui_component": "number",
            "help_text": "Sound reduction in decibels",
            "validation_rules": {"min": 20, "max": 60},
        },
        # Safety and Security
        {
            "name": "safety_rating",
            "description": "Safety rating",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "glazing.safety.safety_rating",
            "depth": 2,
            "sort_order": 13,
            "ui_component": "dropdown",
            "help_text": "Safety classification of the glass",
            "validation_rules": {
                "options": [
                    "Standard",
                    "Tempered",
                    "Laminated",
                    "Security",
                    "Bulletproof",
                    "Fire Rated",
                ]
            },
        },
        {
            "name": "impact_resistance",
            "description": "Impact resistance class",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "glazing.safety.impact_resistance",
            "depth": 2,
            "sort_order": 14,
            "ui_component": "dropdown",
            "help_text": "Impact resistance classification",
            "validation_rules": {
                "options": [
                    "Class 1 (Basic)",
                    "Class 2 (Enhanced)",
                    "Class 3 (High)",
                    "Class 4 (Maximum)",
                ]
            },
        },
        # Dimensions and Installation
        {
            "name": "maximum_size",
            "description": "Maximum size (mm)",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "glazing.dimensions.maximum_size",
            "depth": 2,
            "sort_order": 15,
            "ui_component": "input",
            "help_text": "Maximum glass size (e.g., '2000x3000')",
            "validation_rules": {"max_length": 50},
        },
        {
            "name": "minimum_size",
            "description": "Minimum size (mm)",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "glazing.dimensions.minimum_size",
            "depth": 2,
            "sort_order": 16,
            "ui_component": "input",
            "help_text": "Minimum glass size (e.g., '300x300')",
            "validation_rules": {"max_length": 50},
        },
        {
            "name": "edge_work",
            "description": "Edge work type",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "glazing.dimensions.edge_work",
            "depth": 2,
            "sort_order": 17,
            "ui_component": "dropdown",
            "help_text": "Type of edge finishing",
            "validation_rules": {
                "options": ["Polished", "Ground", "Cut", "Beveled", "Rounded", "Other"]
            },
        },
        # Pricing
        {
            "name": "price_per_sqm",
            "description": "Price per square meter",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.pricing.price_per_sqm",
            "depth": 2,
            "sort_order": 18,
            "ui_component": "currency",
            "help_text": "Price per square meter in local currency",
            "validation_rules": {"min": 0, "max": 1000},
        },
        {
            "name": "installation_cost",
            "description": "Installation cost per sqm",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.pricing.installation_cost",
            "depth": 2,
            "sort_order": 19,
            "ui_component": "currency",
            "help_text": "Installation cost per square meter",
            "validation_rules": {"min": 0, "max": 200},
        },
        {
            "name": "lead_time",
            "description": "Lead time (days)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "glazing.pricing.lead_time",
            "depth": 2,
            "sort_order": 20,
            "ui_component": "number",
            "help_text": "Manufacturing and delivery lead time in days",
            "validation_rules": {"min": 1, "max": 90},
        },
    ]

    # Create attribute nodes
    created_count = 0
    for attr_def in glazing_definitions:
        node = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            parent_node_id=None,  # All are root level for now
            name=attr_def["name"],
            description=attr_def["description"],
            node_type=attr_def["node_type"],
            data_type=attr_def["data_type"],
            required=attr_def["required"],
            ltree_path=attr_def["ltree_path"],
            depth=attr_def["depth"],
            sort_order=attr_def["sort_order"],
            ui_component=attr_def["ui_component"],
            help_text=attr_def["help_text"],
            validation_rules=attr_def.get("validation_rules"),
            display_condition=attr_def.get("display_condition"),
            page_type="glazing",  # Set page_type for glazing attributes
        )
        session.add(node)
        created_count += 1

    await session.commit()
    print(f"  ✅ Created {created_count} glazing attribute nodes")


async def main():
    """Main setup function."""
    print("Setting up Window Glazing Entry attribute hierarchy...")
    print("=" * 70)

    engine = get_engine()
    session_maker = get_session_maker()

    try:
        async with session_maker() as session:
            # Get or create manufacturing type
            manufacturing_type = await get_or_create_manufacturing_type(session)

            # Create glazing attribute nodes
            await create_glazing_attribute_nodes(session, manufacturing_type)

        print("\n" + "=" * 70)
        print("✅ Glazing setup completed successfully!")
        print(f"Manufacturing Type ID: {manufacturing_type.id}")
        print("You can now use the Glazing Entry Page system.")

    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
