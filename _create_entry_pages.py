#!/usr/bin/env python3
"""Create missing entry page attributes for accessories and glazing."""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.database.connection import get_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.models.manufacturing_type import ManufacturingType
from app.models.attribute_node import AttributeNode


async def create_entry_pages():
    """Create accessories and glazing page attributes."""
    print("=== Creating Entry Pages (Accessories & Glazing) ===\n")

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        try:
            # Get the first manufacturing type
            result = await session.execute(select(ManufacturingType).limit(1))
            mfg_type = result.scalar_one_or_none()

            if not mfg_type:
                print("Error: No manufacturing types found!")
                return

            print(f"Using manufacturing type: {mfg_type.name} (ID: {mfg_type.id})")

            # Create accessories page attributes
            print("\nCreating accessories page attributes...")

            accessories_attrs = [
                {
                    "name": "Screen Type",
                    "node_type": "attribute",
                    "data_type": "selection",
                    "required": False,
                    "ltree_path": "accessories.screen_type",
                    "depth": 1,
                    "sort_order": 1,
                    "ui_component": "radio",
                    "description": "Window screen options",
                },
                {
                    "name": "Full Screen",
                    "node_type": "option",
                    "data_type": "selection",
                    "required": False,
                    "ltree_path": "accessories.screen_type.full_screen",
                    "depth": 2,
                    "sort_order": 1,
                    "ui_component": "radio",
                    "description": "Full window screen",
                    "price_impact_value": Decimal("45.00"),
                },
                {
                    "name": "Half Screen",
                    "node_type": "option",
                    "data_type": "selection",
                    "required": False,
                    "ltree_path": "accessories.screen_type.half_screen",
                    "depth": 2,
                    "sort_order": 2,
                    "ui_component": "radio",
                    "description": "Half window screen",
                    "price_impact_value": Decimal("25.00"),
                },
                {
                    "name": "No Screen",
                    "node_type": "option",
                    "data_type": "selection",
                    "required": False,
                    "ltree_path": "accessories.screen_type.no_screen",
                    "depth": 2,
                    "sort_order": 3,
                    "ui_component": "radio",
                    "description": "No screen",
                    "price_impact_value": Decimal("0.00"),
                },
            ]

            # Create glazing page attributes
            print("Creating glazing page attributes...")

            glazing_attrs = [
                {
                    "name": "Glass Type",
                    "node_type": "attribute",
                    "data_type": "selection",
                    "required": True,
                    "ltree_path": "glazing.glass_type",
                    "depth": 1,
                    "sort_order": 1,
                    "ui_component": "radio",
                    "description": "Type of glass",
                },
                {
                    "name": "Single Pane",
                    "node_type": "option",
                    "data_type": "selection",
                    "required": False,
                    "ltree_path": "glazing.glass_type.single_pane",
                    "depth": 2,
                    "sort_order": 1,
                    "ui_component": "radio",
                    "description": "Single pane glass",
                    "price_impact_value": Decimal("0.00"),
                },
                {
                    "name": "Double Pane",
                    "node_type": "option",
                    "data_type": "selection",
                    "required": False,
                    "ltree_path": "glazing.glass_type.double_pane",
                    "depth": 2,
                    "sort_order": 2,
                    "ui_component": "radio",
                    "description": "Double pane glass",
                    "price_impact_value": Decimal("80.00"),
                },
                {
                    "name": "Triple Pane",
                    "node_type": "option",
                    "data_type": "selection",
                    "required": False,
                    "ltree_path": "glazing.glass_type.triple_pane",
                    "depth": 2,
                    "sort_order": 3,
                    "ui_component": "radio",
                    "description": "Triple pane glass",
                    "price_impact_value": Decimal("150.00"),
                },
            ]

            # Set parent relationships for accessories
            accessories_attrs[1]["parent_node_id"] = None  # Will be set after creating parent
            accessories_attrs[2]["parent_node_id"] = None
            accessories_attrs[3]["parent_node_id"] = None

            # Set parent relationships for glazing
            glazing_attrs[1]["parent_node_id"] = None  # Will be set after creating parent
            glazing_attrs[2]["parent_node_id"] = None
            glazing_attrs[3]["parent_node_id"] = None

            # Create accessories attributes
            created_accessories = []
            for attr_data in accessories_attrs:
                attr_node = AttributeNode(
                    manufacturing_type_id=mfg_type.id,
                    page_type="accessories",
                    price_impact_type="fixed",
                    weight_impact=Decimal("0.00"),
                    **attr_data,
                )
                session.add(attr_node)
                await session.flush()
                created_accessories.append(attr_node)

                # Set parent for options
                if attr_data["node_type"] == "option" and len(created_accessories) > 1:
                    attr_node.parent_node_id = created_accessories[0].id

            # Create glazing attributes
            created_glazing = []
            for attr_data in glazing_attrs:
                attr_node = AttributeNode(
                    manufacturing_type_id=mfg_type.id,
                    page_type="glazing",
                    price_impact_type="fixed",
                    weight_impact=Decimal("0.00"),
                    **attr_data,
                )
                session.add(attr_node)
                await session.flush()
                created_glazing.append(attr_node)

                # Set parent for options
                if attr_data["node_type"] == "option" and len(created_glazing) > 1:
                    attr_node.parent_node_id = created_glazing[0].id

            await session.commit()

            print(f"OK: Created {len(accessories_attrs)} accessories attributes")
            print(f"OK: Created {len(glazing_attrs)} glazing attributes")
            print("\nOK: Entry pages setup complete!")

        except Exception as e:
            await session.rollback()
            print(f"Error creating entry pages: {e}")
            raise
        finally:
            await session.close()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_entry_pages())
