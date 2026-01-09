#!/usr/bin/env python3
"""Setup script for Window Accessories Entry manufacturing type and attribute hierarchy.

This script creates attribute nodes for window accessories based on the business
requirements from the reference documents (hinges, handles, locks, hardware).

Usage:
    python setup_accessories_hierarchy.py
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


async def create_accessories_attribute_nodes(
    session: AsyncSession, manufacturing_type: ManufacturingType
) -> None:
    """Create accessories attribute nodes based on business requirements."""
    print("Creating accessories attribute nodes...")

    # Check if accessories nodes already exist
    stmt = select(AttributeNode).where(
        AttributeNode.manufacturing_type_id == manufacturing_type.id,
        AttributeNode.page_type == "accessories",
    )
    result = await session.execute(stmt)
    existing_nodes = result.scalars().all()

    if existing_nodes:
        print(f"  ⚠️  Found {len(existing_nodes)} existing accessories nodes, skipping creation")
        return

    # Define accessories attribute nodes based on reference documents
    accessories_definitions = [
        # Basic Information
        {
            "name": "accessory_name",
            "description": "Accessory name or part number",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "accessories.basic.accessory_name",
            "depth": 2,
            "sort_order": 1,
            "ui_component": "input",
            "help_text": "Enter the accessory name (e.g., '7.5\" Hinge', 'Standard Handle')",
            "validation_rules": {"min_length": 1, "max_length": 200},
        },
        {
            "name": "accessory_type",
            "description": "Type of accessory",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "accessories.basic.accessory_type",
            "depth": 2,
            "sort_order": 2,
            "ui_component": "dropdown",
            "help_text": "Select the accessory category",
            "validation_rules": {
                "options": [
                    "Hinge",
                    "Handle",
                    "Lock",
                    "Espagnolette",
                    "Hardware Set",
                    "Wheel Set",
                    "Track",
                    "Drain Cover",
                    "Nail Stud",
                    "Other",
                ]
            },
        },
        {
            "name": "size_specification",
            "description": "Size or dimension specification",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "accessories.basic.size_specification",
            "depth": 2,
            "sort_order": 3,
            "ui_component": "input",
            "help_text": "Size specification (e.g., '7.5\"', '10cm', '80cm')",
            "validation_rules": {"max_length": 50},
        },
        {
            "name": "material_finish",
            "description": "Material and finish",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "accessories.basic.material_finish",
            "depth": 2,
            "sort_order": 4,
            "ui_component": "dropdown",
            "help_text": "Select material and finish",
            "validation_rules": {
                "options": [
                    "Stainless Steel",
                    "Aluminum",
                    "Brass",
                    "Chrome",
                    "White",
                    "Black",
                    "Bronze",
                    "Other",
                ]
            },
        },
        # Technical Specifications
        {
            "name": "load_capacity",
            "description": "Load capacity (kg)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "accessories.technical.load_capacity",
            "depth": 2,
            "sort_order": 5,
            "ui_component": "number",
            "help_text": "Maximum load capacity in kg (for hinges, wheel sets)",
            "validation_rules": {"min": 0, "max": 200},
            "display_condition": {
                "operator": "in",
                "field": "accessory_type",
                "value": ["Hinge", "Wheel Set"],
            },
        },
        {
            "name": "opening_angle",
            "description": "Maximum opening angle (degrees)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "accessories.technical.opening_angle",
            "depth": 2,
            "sort_order": 6,
            "ui_component": "number",
            "help_text": "Maximum opening angle in degrees (for hinges)",
            "validation_rules": {"min": 0, "max": 180},
            "display_condition": {
                "operator": "equals",
                "field": "accessory_type",
                "value": "Hinge",
            },
        },
        {
            "name": "locking_points",
            "description": "Number of locking points",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "accessories.technical.locking_points",
            "depth": 2,
            "sort_order": 7,
            "ui_component": "number",
            "help_text": "Number of locking points (for espagnolettes, locks)",
            "validation_rules": {"min": 1, "max": 10},
            "display_condition": {
                "operator": "in",
                "field": "accessory_type",
                "value": ["Lock", "Espagnolette"],
            },
        },
        {
            "name": "operation_type",
            "description": "Operation type",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "accessories.technical.operation_type",
            "depth": 2,
            "sort_order": 8,
            "ui_component": "dropdown",
            "help_text": "How the accessory operates",
            "validation_rules": {
                "options": [
                    "Manual",
                    "Key Lock",
                    "Push Button",
                    "Lever",
                    "Tilt & Turn",
                    "Sliding",
                    "Other",
                ]
            },
        },
        # Compatibility
        {
            "name": "compatible_systems",
            "description": "Compatible window systems",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "accessories.compatibility.compatible_systems",
            "depth": 2,
            "sort_order": 9,
            "ui_component": "text",
            "help_text": "List compatible window systems (e.g., 'Kom700, Kom800')",
            "validation_rules": {"max_length": 200},
        },
        {
            "name": "installation_position",
            "description": "Installation position",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "accessories.compatibility.installation_position",
            "depth": 2,
            "sort_order": 10,
            "ui_component": "dropdown",
            "help_text": "Where this accessory is installed",
            "validation_rules": {
                "options": [
                    "Frame",
                    "Sash",
                    "Both",
                    "Track",
                    "Bottom",
                    "Top",
                    "Side",
                    "Corner",
                    "Other",
                ]
            },
        },
        # Pricing
        {
            "name": "unit_price",
            "description": "Unit price",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "accessories.pricing.unit_price",
            "depth": 2,
            "sort_order": 11,
            "ui_component": "currency",
            "help_text": "Price per unit in local currency",
            "validation_rules": {"min": 0, "max": 1000},
        },
        {
            "name": "quantity_per_window",
            "description": "Typical quantity per window",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "accessories.pricing.quantity_per_window",
            "depth": 2,
            "sort_order": 12,
            "ui_component": "number",
            "help_text": "Typical quantity needed per window",
            "validation_rules": {"min": 1, "max": 20},
        },
        # Additional Properties
        {
            "name": "color_options",
            "description": "Available colors",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "accessories.properties.color_options",
            "depth": 2,
            "sort_order": 13,
            "ui_component": "text",
            "help_text": "Available color options (e.g., 'White, Brown, Black')",
            "validation_rules": {"max_length": 200},
        },
        {
            "name": "warranty_period",
            "description": "Warranty period (years)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "accessories.properties.warranty_period",
            "depth": 2,
            "sort_order": 14,
            "ui_component": "number",
            "help_text": "Warranty period in years",
            "validation_rules": {"min": 0, "max": 25},
        },
        {
            "name": "supplier_code",
            "description": "Supplier part code",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "accessories.properties.supplier_code",
            "depth": 2,
            "sort_order": 15,
            "ui_component": "input",
            "help_text": "Supplier's part number or code",
            "validation_rules": {"max_length": 100},
        },
    ]

    # Create attribute nodes
    created_count = 0
    for attr_def in accessories_definitions:
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
            page_type="accessories",  # Set page_type for accessories attributes
        )
        session.add(node)
        created_count += 1

    await session.commit()
    print(f"  ✅ Created {created_count} accessories attribute nodes")


async def main():
    """Main setup function."""
    print("Setting up Window Accessories Entry attribute hierarchy...")
    print("=" * 70)

    engine = get_engine()
    session_maker = get_session_maker()

    try:
        async with session_maker() as session:
            # Get or create manufacturing type
            manufacturing_type = await get_or_create_manufacturing_type(session)

            # Create accessories attribute nodes
            await create_accessories_attribute_nodes(session, manufacturing_type)

        print("\n" + "=" * 70)
        print("✅ Accessories setup completed successfully!")
        print(f"Manufacturing Type ID: {manufacturing_type.id}")
        print("You can now use the Accessories Entry Page system.")

    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
