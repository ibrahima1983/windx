#!/usr/bin/env python3
"""Setup script for Window Profile Entry manufacturing type and attribute hierarchy.

This script creates the "Window Profile Entry" manufacturing type and builds
all 29 CSV column attribute nodes with proper data types, validation rules,
and conditional display logic.

Usage:
    python setup_profile_hierarchy.py
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


async def create_manufacturing_type(session: AsyncSession) -> ManufacturingType:
    """Create Window Profile Entry manufacturing type."""
    print("Creating Window Profile Entry manufacturing type...")

    # Check if it already exists
    stmt = select(ManufacturingType).where(ManufacturingType.name == "Window Profile Entry")
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        print(f"  ✅ Manufacturing type already exists (ID: {existing.id})")
        return existing

    # Create new manufacturing type
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


async def create_attribute_nodes(
    session: AsyncSession, manufacturing_type: ManufacturingType
) -> None:
    """Create all 29 CSV column attribute nodes."""
    print("Creating attribute nodes for all 29 CSV columns...")

    # Define all attribute nodes based on CSV structure
    attribute_definitions = [
        # Basic Information Section
        {
            "name": "name",
            "description": "Product name",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.name",
            "depth": 1,
            "sort_order": 1,
            "ui_component": "input",
            "help_text": "Enter a descriptive name for this profile",
            "validation_rules": {"min_length": 1, "max_length": 200},
        },
        {
            "name": "type",
            "description": "Product type",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.type",
            "depth": 1,
            "sort_order": 2,
            "ui_component": "dropdown",
            "help_text": "Select the product type",
            "validation_rules": {
                "options": [
                    "Frame",
                    "Sash",
                    "Mullion",
                    "Flying mullion",
                    "Glazing bead",
                    "Interlock",
                    "Track",
                    "Auxiliary",
                    "Coupling",
                    "Tube",
                ]
            },
        },
        {
            "name": "company",
            "description": "Company",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "basic_information.company",
            "depth": 1,
            "sort_order": 3,
            "ui_component": "dropdown",
            "help_text": "Company or manufacturer name",
            "validation_rules": {"max_length": 100},
        },
        {
            "name": "material",
            "description": "Material",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.material",
            "depth": 1,
            "sort_order": 4,
            "ui_component": "dropdown",
            "help_text": "Select the material type",
            "validation_rules": {"options": ["UPVC", "Aluminum", "Wood", "Steel", "Composite"]},
        },
        {
            "name": "opening_system",
            "description": "Opening System",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.opening_system",
            "depth": 1,
            "sort_order": 5,
            "ui_component": "dropdown",
            "help_text": "Select the opening system type",
            "validation_rules": {
                "options": ["Casement", "Sliding", "Double-hung", "Tilt-turn", "Fixed", "All"]
            },
        },
        {
            "name": "system_series",
            "description": "System Series",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.system_series",
            "depth": 1,
            "sort_order": 6,
            "ui_component": "input",
            "help_text": "Enter the system series (e.g., Kom700, Kom800)",
            "validation_rules": {"max_length": 50},
        },
        {
            "name": "code",
            "description": "Product Code",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "basic_information.code",
            "depth": 1,
            "sort_order": 7,
            "ui_component": "input",
            "help_text": "Product code or SKU",
            "validation_rules": {"max_length": 50},
        },
        {
            "name": "length_of_beam",
            "description": "Length of Beam (m)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "basic_information.length_of_beam",
            "depth": 1,
            "sort_order": 8,
            "ui_component": "number",
            "help_text": "Length of beam in meters",
            "validation_rules": {"min": 0, "max": 20},
        },
        # Conditional Fields Section
        {
            "name": "renovation",
            "description": "Renovation (only for frame)",
            "node_type": "attribute",
            "data_type": "boolean",
            "required": False,
            "ltree_path": "conditional_fields.renovation",
            "depth": 1,
            "sort_order": 9,
            "ui_component": "checkbox",
            "help_text": "Check if this is for renovation purposes",
            "display_condition": {"operator": "equals", "field": "type", "value": "Frame"},
        },
        {
            "name": "builtin_flyscreen_track",
            "description": "Built-in Flyscreen Track (only for sliding frame)",
            "node_type": "attribute",
            "data_type": "boolean",
            "required": False,
            "ltree_path": "conditional_fields.builtin_flyscreen_track",
            "depth": 1,
            "sort_order": 10,
            "ui_component": "checkbox",
            "help_text": "Check if frame has built-in flyscreen track",
            "display_condition": {
                "operator": "and",
                "conditions": [
                    {"operator": "equals", "field": "type", "value": "Frame"},
                    {"operator": "contains", "field": "opening_system", "value": "sliding"},
                ],
            },
        },
        # Dimensions Section
        {
            "name": "width",
            "description": "Width",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.width",
            "depth": 1,
            "sort_order": 11,
            "ui_component": "number",
            "help_text": "Width dimension in mm",
            "validation_rules": {"min": 0, "max": 5000},
        },
        {
            "name": "total_width",
            "description": "Total Width (only for frame with built-in flyscreen)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.total_width",
            "depth": 1,
            "sort_order": 12,
            "ui_component": "number",
            "help_text": "Total width including flyscreen track",
            "validation_rules": {"min": 0, "max": 5000},
            "display_condition": {
                "operator": "equals",
                "field": "builtin_flyscreen_track",
                "value": True,
            },
        },
        {
            "name": "flyscreen_track_height",
            "description": "Flyscreen Track Height (only for frame with built-in flyscreen)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.flyscreen_track_height",
            "depth": 1,
            "sort_order": 13,
            "ui_component": "number",
            "help_text": "Height of flyscreen track in mm",
            "validation_rules": {"min": 0, "max": 200},
            "display_condition": {
                "operator": "equals",
                "field": "builtin_flyscreen_track",
                "value": True,
            },
        },
        {
            "name": "front_height",
            "description": "Front Height (mm)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.front_height",
            "depth": 1,
            "sort_order": 14,
            "ui_component": "number",
            "help_text": "Front height in mm",
            "validation_rules": {"min": 0, "max": 5000},
        },
        {
            "name": "rear_height",
            "description": "Rear Height",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.rear_height",
            "depth": 1,
            "sort_order": 15,
            "ui_component": "number",
            "help_text": "Rear height in mm",
            "validation_rules": {"min": 0, "max": 5000},
        },
        {
            "name": "glazing_height",
            "description": "Glazing Height",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.glazing_height",
            "depth": 1,
            "sort_order": 16,
            "ui_component": "number",
            "help_text": "Glazing height in mm",
            "validation_rules": {"min": 0, "max": 5000},
        },
        {
            "name": "renovation_height",
            "description": "Renovation Height (mm, only for frame)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.renovation_height",
            "depth": 1,
            "sort_order": 17,
            "ui_component": "number",
            "help_text": "Renovation height in mm",
            "validation_rules": {"min": 0, "max": 5000},
            "display_condition": {"operator": "equals", "field": "type", "value": "Frame"},
        },
        {
            "name": "glazing_undercut_height",
            "description": "Glazing Undercut Height (only for glazing bead)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.glazing_undercut_height",
            "depth": 1,
            "sort_order": 18,
            "ui_component": "number",
            "help_text": "Glazing undercut height in mm",
            "validation_rules": {"min": 0, "max": 100},
            "display_condition": {"operator": "equals", "field": "type", "value": "Glazing bead"},
        },
        # Technical Specifications Section
        {
            "name": "pic",
            "description": "Picture/Image",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "technical_specs.pic",
            "depth": 1,
            "sort_order": 19,
            "ui_component": "file",
            "help_text": "Image filename or reference",
            "validation_rules": {"max_length": 200},
        },
        {
            "name": "sash_overlap",
            "description": "Sash Overlap (only for sashes)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "technical_specs.sash_overlap",
            "depth": 1,
            "sort_order": 20,
            "ui_component": "number",
            "help_text": "Sash overlap in mm",
            "validation_rules": {"min": 0, "max": 50},
            "display_condition": {"operator": "equals", "field": "type", "value": "Sash"},
        },
        {
            "name": "flying_mullion_horizontal_clearance",
            "description": "Flying Mullion Horizontal Clearance",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "technical_specs.flying_mullion_horizontal_clearance",
            "depth": 1,
            "sort_order": 21,
            "ui_component": "number",
            "help_text": "Horizontal clearance for flying mullion in mm",
            "validation_rules": {"min": 0, "max": 100},
            "display_condition": {"operator": "equals", "field": "type", "value": "Flying mullion"},
        },
        {
            "name": "flying_mullion_vertical_clearance",
            "description": "Flying Mullion Vertical Clearance",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "technical_specs.flying_mullion_vertical_clearance",
            "depth": 1,
            "sort_order": 22,
            "ui_component": "number",
            "help_text": "Vertical clearance for flying mullion in mm",
            "validation_rules": {"min": 0, "max": 100},
            "display_condition": {"operator": "equals", "field": "type", "value": "Flying mullion"},
        },
        {
            "name": "steel_material_thickness",
            "description": "Steel Material Thickness (only for reinforcement)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "technical_specs.steel_material_thickness",
            "depth": 1,
            "sort_order": 23,
            "ui_component": "number",
            "help_text": "Steel thickness in mm",
            "validation_rules": {"min": 0, "max": 10},
            "display_condition": {
                "operator": "is_not_empty",
                "field": "reinforcement_steel",
                "value": None,
            },
        },
        {
            "name": "weight_per_meter",
            "description": "Weight per Meter (kg)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "technical_specs.weight_per_meter",
            "depth": 1,
            "sort_order": 24,
            "ui_component": "number",
            "help_text": "Weight per meter in kg",
            "validation_rules": {"min": 0, "max": 2000},
        },
        {
            "name": "reinforcement_steel",
            "description": "Reinforcement Steel",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "technical_specs.reinforcement_steel",
            "depth": 1,
            "sort_order": 25,
            "ui_component": "dropdown",
            "help_text": "Select reinforcement steel options",
        },
        {
            "name": "colours",
            "description": "Available Colors",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "technical_specs.colours",
            "depth": 1,
            "sort_order": 26,
            "ui_component": "dropdown",
            "help_text": "Select available colors",
        },
        # Pricing Section
        {
            "name": "price_per_meter",
            "description": "Price per Meter",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "pricing.price_per_meter",
            "depth": 1,
            "sort_order": 27,
            "ui_component": "currency",
            "help_text": "Price per meter in currency units",
            "validation_rules": {"min": 0, "max": 10000},
        },
        {
            "name": "price_per_beam",
            "description": "Price per Beam",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "pricing.price_per_beam",
            "depth": 1,
            "sort_order": 28,
            "ui_component": "currency",
            "help_text": "Price per beam in currency units",
            "validation_rules": {"min": 0, "max": 50000},
        },
        {
            "name": "upvc_profile_discount",
            "description": "UPVC Profile Discount (%)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "pricing.upvc_profile_discount",
            "depth": 1,
            "sort_order": 29,
            "ui_component": "percentage",
            "help_text": "Discount percentage for UPVC profiles",
            "validation_rules": {"min": 0, "max": 100},
        },
    ]

    # Check if nodes already exist
    stmt = select(AttributeNode).where(AttributeNode.manufacturing_type_id == manufacturing_type.id)
    result = await session.execute(stmt)
    existing_nodes = result.scalars().all()

    # Comprehensive tooltip content for all fields
    tooltip_content = {
        "name": {
            "description": "A unique identifier for this profile.<br><br><strong>Examples:</strong><br>• 'Standard Casement Window'<br>• 'Premium Sliding Door'<br>• 'Economy Frame Profile'<br><br><strong>Tip:</strong> Use descriptive names that clearly identify the product type and variant.",
            "help_text": "This name will be used in reports, quotes, and inventory listings. Make it descriptive enough to distinguish between similar profiles."
        },
        "type": {
            "description": "The category of this profile component.<br><br><strong>Options:</strong><br>• <strong>Frame</strong> - Main structural component that holds the glass<br>• <strong>Sash</strong> - Movable window panel<br>• <strong>Mullion</strong> - Vertical or horizontal divider<br>• <strong>Glazing Bead</strong> - Strip that holds glass in place<br>• <strong>Track</strong> - Sliding mechanism component",
            "help_text": "Select the type that best describes this profile's function in the window or door assembly."
        },
        "company": {
            "description": "The manufacturer or supplier of this profile system.<br><br><strong>Use:</strong><br>• Select from your database of approved suppliers<br>• Affects pricing, availability, and compatibility<br>• Used for inventory tracking and ordering<br><br><strong>Note:</strong> Different companies may have incompatible profile systems.",
            "help_text": "Ensure all components in a project use compatible systems from the same manufacturer."
        },
        "material": {
            "description": "The primary material composition of the profile.<br><br><strong>Common Options:</strong><br>• <strong>UPVC</strong> - Durable, low-maintenance plastic (most common)<br>• <strong>Aluminum</strong> - Strong, corrosion-resistant metal<br>• <strong>Wood</strong> - Traditional, natural material<br>• <strong>Composite</strong> - Combination of materials<br><br><strong>Properties:</strong><br>• Affects thermal performance<br>• Determines maintenance requirements<br>• Impacts pricing",
            "help_text": "UPVC is the most popular choice for residential applications due to its durability and low maintenance."
        },
        "opening_system": {
            "description": "The window or door opening mechanism type.<br><br><strong>Common Types:</strong><br>• <strong>Casement</strong> - Hinged window that opens outward<br>• <strong>Sliding</strong> - Horizontal sliding panels<br>• <strong>Tilt & Turn</strong> - Dual-action opening<br>• <strong>Fixed</strong> - Non-opening window<br>• <strong>Awning</strong> - Top-hinged, opens outward<br><br><strong>Selection Criteria:</strong><br>• Space availability<br>• Ventilation needs<br>• Ease of cleaning",
            "help_text": "The opening system affects hardware requirements, pricing, and installation complexity."
        },
        "system_series": {
            "description": "The specific profile system series from the manufacturer.<br><br><strong>Examples:</strong><br>• Kom700 - Standard residential series<br>• Kom701 - Enhanced thermal performance<br>• Kom800 - Premium commercial series<br><br><strong>Series Differences:</strong><br>• Chamber count (thermal efficiency)<br>• Wall thickness (strength)<br>• Glass capacity<br>• Price point",
            "help_text": "Higher series numbers typically indicate better performance and higher cost. Verify compatibility with other components."
        },
        "width": {
            "description": "The width of the profile cross-section in millimeters.<br><br><strong>Measurement:</strong><br>• Measure the actual profile width<br>• Include any flanges or extensions<br>• Exclude gaskets and seals<br><br><strong>Common Widths:</strong><br>• Frame profiles: 60-90mm<br>• Sash profiles: 50-70mm<br>• Mullions: 40-60mm<br><br><strong>Impact:</strong><br>• Affects glass capacity<br>• Determines thermal performance<br>• Influences material cost",
            "help_text": "Wider profiles generally provide better insulation but cost more. Verify compatibility with glass thickness."
        },
        "upvc_profile_discount": {
            "description": "Percentage discount applied to UPVC profile pricing.<br><br><strong>Usage:</strong><br>• Standard discount: 15-25%<br>• Volume discount: up to 40%<br>• Promotional discount: varies<br><br><strong>Application:</strong><br>• Applied to base profile price<br>• Before other calculations<br>• Affects final quote pricing<br><br><strong>Example:</strong><br>• Base price: $100/meter<br>• 20% discount: Final = $80/meter",
            "help_text": "This discount is typically negotiated with suppliers based on volume commitments. Update regularly based on current agreements."
        },
        "price_per_meter": {
            "description": "The cost per linear meter of this profile in your local currency.<br><br><strong>Includes:</strong><br>• Base material cost<br>• Manufacturing overhead<br>• Supplier markup<br><br><strong>Excludes:</strong><br>• Installation labor<br>• Hardware and accessories<br>• Glass and glazing<br><br><strong>Note:</strong> This is the list price before any discounts are applied.",
            "help_text": "Update this price regularly to reflect current supplier pricing. Use for cost estimation and quoting."
        },
        "weight_per_meter": {
            "description": "The weight of the profile per linear meter in kilograms.<br><br><strong>Purpose:</strong><br>• Shipping cost calculations<br>• Structural load analysis<br>• Hardware sizing<br>• Installation planning<br><br><strong>Typical Values:</strong><br>• Light profiles: 0.5-1.0 kg/m<br>• Standard profiles: 1.0-2.0 kg/m<br>• Heavy profiles: 2.0-4.0 kg/m",
            "help_text": "Heavier profiles generally indicate thicker walls and better structural performance but increase shipping costs."
        },
        # Add more tooltip content for other fields as needed
    }

    if existing_nodes:
        print(f"  ⚠️  Found {len(existing_nodes)} existing nodes, updating metadata and tooltips...")
        existing_map = {n.name: n for n in existing_nodes}
        
        updated_count = 0
        for attr_def in attribute_definitions:
            if attr_def["name"] in existing_map:
                node = existing_map[attr_def["name"]]
                node.sort_order = attr_def["sort_order"]
                node.ui_component = attr_def["ui_component"]
                node.validation_rules = attr_def.get("validation_rules")
                node.display_condition = attr_def.get("display_condition")
                
                # Update with rich tooltip content if available
                if attr_def["name"] in tooltip_content:
                    node.description = tooltip_content[attr_def["name"]]["description"]
                    node.help_text = tooltip_content[attr_def["name"]]["help_text"]
                else:
                    node.description = attr_def["description"]
                    node.help_text = attr_def["help_text"]
                
                updated_count += 1
        
        await session.commit()
        print(f"  ✅ Updated {updated_count} attribute nodes with tooltips")
        return

    # Create attribute nodes if not existing
    created_count = 0
    for attr_def in attribute_definitions:
        # Use rich tooltip content if available, otherwise use basic description
        if attr_def["name"] in tooltip_content:
            description = tooltip_content[attr_def["name"]]["description"]
            help_text = tooltip_content[attr_def["name"]]["help_text"]
        else:
            description = attr_def["description"]
            help_text = attr_def["help_text"]
        
        node = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            parent_node_id=None,  # All are root level for now
            name=attr_def["name"],
            description=description,
            node_type=attr_def["node_type"],
            data_type=attr_def["data_type"],
            required=attr_def["required"],
            ltree_path=attr_def["ltree_path"],
            depth=attr_def["depth"],
            sort_order=attr_def["sort_order"],
            ui_component=attr_def["ui_component"],
            help_text=help_text,
            validation_rules=attr_def.get("validation_rules"),
            display_condition=attr_def.get("display_condition"),
            page_type="profile",  # Set page_type for profile attributes
        )
        session.add(node)
        created_count += 1

    await session.commit()
    print(f"  ✅ Created {created_count} attribute nodes with comprehensive tooltips")


async def main():
    """Main setup function."""
    print("Setting up Window Profile Entry manufacturing type and attribute hierarchy...")
    print("=" * 70)

    engine = get_engine()
    session_maker = get_session_maker()

    try:
        async with session_maker() as session:
            # Create manufacturing type
            manufacturing_type = await create_manufacturing_type(session)

            # Create attribute nodes
            await create_attribute_nodes(session, manufacturing_type)

        print("\n" + "=" * 70)
        print("✅ Setup completed successfully!")
        print(f"Manufacturing Type ID: {manufacturing_type.id}")
        print("You can now use the Entry Page system with this manufacturing type.")

    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
