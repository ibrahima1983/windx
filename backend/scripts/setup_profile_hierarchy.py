#!/usr/bin/env python3
"""Setup script for Window Profile Entry manufacturing type and attribute hierarchy.

This script creates the "Window Profile Entry" manufacturing type and builds
all 29 CSV column attribute nodes with proper data types, validation rules,
conditional display logic, and option nodes for dropdown fields.

Usage:
    python setup_profile_hierarchy_fixed.py
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
        print(f"  Manufacturing type already exists (ID: {existing.id})")
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

    print(f"  Created manufacturing type (ID: {manufacturing_type.id})")
    return manufacturing_type


async def create_option_nodes_for_field(
    session: AsyncSession, parent_node: AttributeNode, options: list[str]
):
    """Create option nodes for a dropdown field."""
    print(f"  Creating {len(options)} option nodes for field: {parent_node.name}")

    # Get existing options to avoid duplicates
    stmt = select(AttributeNode).where(
        AttributeNode.parent_node_id == parent_node.id, AttributeNode.node_type == "option"
    )
    result = await session.execute(stmt)
    existing_options = {node.name for node in result.scalars().all()}

    created_count = 0
    for i, option_value in enumerate(options):
        if option_value not in existing_options:
            option_node = AttributeNode(
                manufacturing_type_id=parent_node.manufacturing_type_id,
                parent_node_id=parent_node.id,
                page_type=parent_node.page_type,
                name=option_value,
                node_type="option",
                data_type="selection",
                ltree_path=f"{parent_node.ltree_path}.{option_value.lower().replace(' ', '_').replace('-', '_')}",
                depth=parent_node.depth + 1,
                sort_order=i + 1,
                price_impact_type="fixed",
                price_impact_value=Decimal("0.00"),
                weight_impact=Decimal("0.00"),
            )
            session.add(option_node)
            created_count += 1

    if created_count > 0:
        await session.commit()
        print(f"    Created {created_count} new options")
    else:
        print(f"    All options already exist")


async def create_attribute_nodes(
    session: AsyncSession, manufacturing_type: ManufacturingType
) -> None:
    """Create all 29 CSV column attribute nodes with proper option hierarchy."""
    print("Creating attribute nodes for all 29 CSV columns...")

    # Define all attribute nodes based on CSV structure
    # Note: No hardcoded validation_rules with options - these will be created as child nodes
    attribute_definitions = [
        # Basic Information Section
        {
            "name": "name",
            "display_name": "Product Name",
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
            "display_name": "Profile Type",
            "description": "Product type",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.type",
            "depth": 1,
            "sort_order": 2,
            "ui_component": "dropdown",
            "help_text": "Select the product type",
            "validation_rules": {},  # No hardcoded options
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
            ],
        },
        {
            "name": "company",
            "display_name": "Company",
            "description": "Company",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "basic_information.company",
            "depth": 1,
            "sort_order": 4,  # Moved after system_series
            "ui_component": "dropdown",
            "help_text": "Company or manufacturer name",
            "validation_rules": {"max_length": 100},
            # No hardcoded options - options come from the relations system (company entity type)
        },
        {
            "name": "material",
            "display_name": "Material",
            "description": "Material",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.material",
            "depth": 1,
            "sort_order": 5,  # Moved after company
            "ui_component": "dropdown",
            "help_text": "Select the material type",
            "validation_rules": {},
            # No hardcoded options - options come from the relations system (material entity type)
        },
        {
            "name": "opening_system",
            "display_name": "Opening System",
            "description": "Opening System",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.opening_system",
            "depth": 1,
            "sort_order": 6,  # Moved after material
            "ui_component": "dropdown",
            "help_text": "Select the opening system type",
            "validation_rules": {},
            # No hardcoded options - options come from the relations system (opening_system entity type)
        },
        {
            "name": "system_series",
            "display_name": "System Series",
            "description": "System Series",
            "node_type": "attribute",
            "data_type": "string",
            "required": True,
            "ltree_path": "basic_information.system_series",
            "depth": 1,
            "sort_order": 3,  # Moved to position 3
            "ui_component": "dropdown",
            "help_text": "Select a system series (e.g., K700, K800)",
            "validation_rules": {"max_length": 200},
            # No hardcoded options - options come from the relations system (system_series entity type)
        },
        {
            "name": "code",
            "display_name": "Product Code",
            "description": "Product Code",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "basic_information.code",
            "depth": 1,
            "sort_order": 8,  # Moved after colours
            "ui_component": "input",
            "help_text": "Product code or SKU",
            "validation_rules": {"max_length": 50},
        },
        {
            "name": "length_of_beam",
            "display_name": "Length of Beam (m)",
            "description": "Length of Beam (m)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "basic_information.length_of_beam",
            "depth": 1,
            "sort_order": 9,  # Updated after code
            "ui_component": "number",
            "help_text": "Length of beam in meters",
            "validation_rules": {"min": 0, "max": 20},
        },
        # Conditional Fields Section
        {
            "name": "renovation",
            "display_name": "Renovation",
            "description": "Renovation (only for frame)",
            "node_type": "attribute",
            "data_type": "boolean",
            "required": False,
            "ltree_path": "conditional_fields.renovation",
            "depth": 1,
            "sort_order": 10,  # Updated
            "ui_component": "checkbox",
            "help_text": "Check if this is for renovation purposes",
            "display_condition": {"operator": "equals", "field": "type", "value": "Frame"},
        },
        {
            "name": "builtin_flyscreen_track",
            "display_name": "Built-in Flyscreen Track",
            "description": "Built-in Flyscreen Track (only for sliding frame)",
            "node_type": "attribute",
            "data_type": "boolean",
            "required": False,
            "ltree_path": "conditional_fields.builtin_flyscreen_track",
            "depth": 1,
            "sort_order": 11,  # Updated
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
            "display_name": "Width (mm)",
            "description": "Width",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.width",
            "depth": 1,
            "sort_order": 12,  # Updated
            "ui_component": "number",
            "help_text": "Width dimension in mm",
            "validation_rules": {"min": 0, "max": 5000},
        },
        {
            "name": "total_width",
            "display_name": "Total Width (mm)",
            "description": "Total Width (only for frame with built-in flyscreen)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "dimensions.total_width",
            "depth": 1,
            "sort_order": 13,  # Updated
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
            "sort_order": 14,  # Updated
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
            "sort_order": 15,  # Updated
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
            "sort_order": 16,  # Updated
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
            "sort_order": 17,  # Updated
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
            "sort_order": 18,  # Updated
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
            "sort_order": 19,  # Updated
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
            "sort_order": 20,  # Updated
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
            "sort_order": 21,  # Updated
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
            "sort_order": 22,  # Updated
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
            "sort_order": 23,  # Updated
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
            "sort_order": 24,  # Updated
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
            "sort_order": 25,  # Updated
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
            "sort_order": 26,  # Updated
            "ui_component": "dropdown",
            "help_text": "Select reinforcement steel options",
            "validation_rules": {},
            # No hardcoded options - options come from the relations system (reinforcement_steel entity type)
        },
        {
            "name": "colours",
            "description": "Available Colors",
            "node_type": "attribute",
            "data_type": "string",
            "required": False,
            "ltree_path": "technical_specs.colours",
            "depth": 1,
            "sort_order": 7,  # Moved after opening_system
            "ui_component": "multi-select",  # Changed to multi-select
            "help_text": "Select available colors (multiple selection)",
            "validation_rules": {},
            # No hardcoded options - options come from the relations system (colours entity type)
        },
        # Pricing Section
        {
            "name": "price_per_meter",
            "display_name": "Price/m",
            "description": "Price per Meter",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "pricing.price_per_meter",
            "depth": 1,
            "sort_order": 27,  # Updated
            "ui_component": "currency",
            "help_text": "Price per meter in currency units",
            "validation_rules": {"min": 0, "max": 10000},
        },
        {
            "name": "price_per_beam",
            "display_name": "Price per Beam",
            "description": "Price per Beam",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "pricing.price_per_beam",
            "depth": 1,
            "sort_order": 28,  # Updated
            "ui_component": "currency",
            "help_text": "Price per beam in currency units",
            "validation_rules": {"min": 0, "max": 50000},
        },
        {
            "name": "upvc_profile_discount",
            "display_name": "UPVC Profile Discount %",
            "description": "UPVC Profile Discount (%)",
            "node_type": "attribute",
            "data_type": "number",
            "required": False,
            "ltree_path": "pricing.upvc_profile_discount",
            "depth": 1,
            "sort_order": 29,  # Updated
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
            "help_text": "This name will be used in reports, quotes, and inventory listings. Make it descriptive enough to distinguish between similar profiles.",
        },
        "type": {
            "description": "The category of this profile component.<br><br><strong>Options:</strong><br>• <strong>Frame</strong> - Main structural component that holds the glass<br>• <strong>Sash</strong> - Movable window panel<br>• <strong>Mullion</strong> - Vertical or horizontal divider<br>• <strong>Glazing Bead</strong> - Strip that holds glass in place<br>• <strong>Track</strong> - Sliding mechanism component",
            "help_text": "Select the type that best describes this profile's function in the window or door assembly.",
        },
        "company": {
            "description": "The manufacturer or supplier of this profile system.<br><br><strong>Use:</strong><br>• Select from your database of approved suppliers<br>• Affects pricing, availability, and compatibility<br>• Used for inventory tracking and ordering<br><br><strong>Note:</strong> Different companies may have incompatible profile systems.",
            "help_text": "Ensure all components in a project use compatible systems from the same manufacturer.",
        },
        "material": {
            "description": "The primary material composition of the profile.<br><br><strong>Common Options:</strong><br>• <strong>UPVC</strong> - Durable, low-maintenance plastic (most common)<br>• <strong>Aluminum</strong> - Strong, corrosion-resistant metal<br>• <strong>Wood</strong> - Traditional, natural material<br>• <strong>Composite</strong> - Combination of materials<br><br><strong>Properties:</strong><br>• Affects thermal performance<br>• Determines maintenance requirements<br>• Impacts pricing",
            "help_text": "UPVC is the most popular choice for residential applications due to its durability and low maintenance.",
        },
        "opening_system": {
            "description": "The window or door opening mechanism type.<br><br><strong>Common Types:</strong><br>• <strong>Casement</strong> - Hinged window that opens outward<br>• <strong>Sliding</strong> - Horizontal sliding panels<br>• <strong>Tilt & Turn</strong> - Dual-action opening<br>• <strong>Fixed</strong> - Non-opening window<br>• <strong>Awning</strong> - Top-hinged, opens outward<br><br><strong>Selection Criteria:</strong><br>• Space availability<br>• Ventilation needs<br>• Ease of cleaning",
            "help_text": "The opening system affects hardware requirements, pricing, and installation complexity.",
        },
        "system_series": {
            "description": "The specific profile system series from the manufacturer.<br><br><strong>Examples:</strong><br>• Kom700 - Standard residential series<br>• Kom701 - Enhanced thermal performance<br>• Kom800 - Premium commercial series<br><br><strong>Series Differences:</strong><br>• Chamber count (thermal efficiency)<br>• Wall thickness (strength)<br>• Glass capacity<br>• Price point",
            "help_text": "Higher series numbers typically indicate better performance and higher cost. Verify compatibility with other components.",
        },
        "width": {
            "description": "The width of the profile cross-section in millimeters.<br><br><strong>Measurement:</strong><br>• Measure the actual profile width<br>• Include any flanges or extensions<br>• Exclude gaskets and seals<br><br><strong>Common Widths:</strong><br>• Frame profiles: 60-90mm<br>• Sash profiles: 50-70mm<br>• Mullions: 40-60mm<br><br><strong>Impact:</strong><br>• Affects glass capacity<br>• Determines thermal performance<br>• Influences material cost",
            "help_text": "Wider profiles generally provide better insulation but cost more. Verify compatibility with glass thickness.",
        },
        "upvc_profile_discount": {
            "description": "Percentage discount applied to UPVC profile pricing.<br><br><strong>Usage:</strong><br>• Standard discount: 15-25%<br>• Volume discount: up to 40%<br>• Promotional discount: varies<br><br><strong>Application:</strong><br>• Applied to base profile price<br>• Before other calculations<br>• Affects final quote pricing<br><br><strong>Example:</strong><br>• Base price: $100/meter<br>• 20% discount: Final = $80/meter",
            "help_text": "This discount is typically negotiated with suppliers based on volume commitments. Update regularly based on current agreements.",
        },
        "price_per_meter": {
            "description": "The cost per linear meter of this profile in your local currency.<br><br><strong>Includes:</strong><br>• Base material cost<br>• Manufacturing overhead<br>• Supplier markup<br><br><strong>Excludes:</strong><br>• Installation labor<br>• Hardware and accessories<br>• Glass and glazing<br><br><strong>Note:</strong> This is the list price before any discounts are applied.",
            "help_text": "Update this price regularly to reflect current supplier pricing. Use for cost estimation and quoting.",
        },
        "weight_per_meter": {
            "description": "The weight of the profile per linear meter in kilograms.<br><br><strong>Purpose:</strong><br>• Shipping cost calculations<br>• Structural load analysis<br>• Hardware sizing<br>• Installation planning<br><br><strong>Typical Values:</strong><br>• Light profiles: 0.5-1.0 kg/m<br>• Standard profiles: 1.0-2.0 kg/m<br>• Heavy profiles: 2.0-4.0 kg/m",
            "help_text": "Heavier profiles generally indicate thicker walls and better structural performance but increase shipping costs.",
        },
        "code": {
            "description": "A unique product code or SKU for inventory and ordering purposes.<br><br><strong>Format:</strong><br>• Use consistent naming convention<br>• Include manufacturer prefix if needed<br>• Examples: 'KOM700-FR', 'ALU-SASH-60'<br><br><strong>Purpose:</strong><br>• Inventory tracking<br>• Order processing<br>• Quality control<br>• Documentation",
            "help_text": "This code should match your supplier's part number for easy ordering and inventory management.",
        },
        "length_of_beam": {
            "description": "The standard length of profile beams available from the supplier.<br><br><strong>Common Lengths:</strong><br>• Residential: 6m (20 feet)<br>• Commercial: 6-12m (20-40 feet)<br>• Custom: Variable lengths<br><br><strong>Considerations:</strong><br>• Transportation limits<br>• Waste minimization<br>• Installation efficiency",
            "help_text": "Longer beams reduce joints but may be harder to transport and handle on site.",
        },
        "renovation": {
            "description": "Indicates if this profile is designed for renovation applications.<br><br><strong>Renovation Features:</strong><br>• Reduced depth for existing openings<br>• Special mounting systems<br>• Compatibility with existing frames<br>• Minimal disruption installation<br><br><strong>Benefits:</strong><br>• Faster installation<br>• Less structural work<br>• Cost-effective upgrades",
            "help_text": "Renovation profiles are specifically designed to fit into existing window openings with minimal modification.",
        },
        "builtin_flyscreen_track": {
            "description": "Integrated track system for flyscreen installation.<br><br><strong>Features:</strong><br>• Built-in guide rails<br>• Smooth operation<br>• Weather sealing<br>• Easy maintenance<br><br><strong>Benefits:</strong><br>• Cleaner appearance<br>• Better performance<br>• Reduced installation time<br>• Improved durability",
            "help_text": "Built-in tracks provide better integration and performance compared to add-on flyscreen systems.",
        },
        "total_width": {
            "description": "Total width including the built-in flyscreen track system.<br><br><strong>Measurement:</strong><br>• Frame width + track width<br>• Important for rough opening sizing<br>• Affects installation clearances<br><br><strong>Planning:</strong><br>• Check available space<br>• Consider wall thickness<br>• Plan for proper sealing",
            "help_text": "This dimension is critical for ensuring proper fit in the wall opening when flyscreen tracks are included.",
        },
        "flyscreen_track_height": {
            "description": "Height of the integrated flyscreen track system.<br><br><strong>Specifications:</strong><br>• Track depth in millimeters<br>• Affects screen operation<br>• Impacts weather sealing<br><br><strong>Considerations:</strong><br>• Screen type compatibility<br>• Operating clearance<br>• Maintenance access",
            "help_text": "Proper track height ensures smooth flyscreen operation and effective insect protection.",
        },
        "front_height": {
            "description": "Height of the profile's front face in millimeters.<br><br><strong>Measurement:</strong><br>• From bottom to top of visible face<br>• Affects appearance and proportions<br>• Important for glazing calculations<br><br><strong>Design Impact:</strong><br>• Visual weight of the frame<br>• Glass area maximization<br>• Structural requirements",
            "help_text": "Front height affects both the aesthetic appearance and the amount of daylight entering through the window.",
        },
        "rear_height": {
            "description": "Height of the profile's rear face in millimeters.<br><br><strong>Purpose:</strong><br>• Structural support<br>• Installation clearance<br>• Insulation space<br>• Hardware mounting<br><br><strong>Considerations:</strong><br>• Wall cavity depth<br>• Insulation requirements<br>• Fixing methods",
            "help_text": "Rear height must accommodate wall thickness and provide adequate space for proper installation and insulation.",
        },
        "glazing_height": {
            "description": "Height available for glazing installation in millimeters.<br><br><strong>Calculation:</strong><br>• Total height minus frame components<br>• Determines maximum glass size<br>• Affects glazing bead selection<br><br><strong>Optimization:</strong><br>• Maximize daylight<br>• Ensure structural integrity<br>• Meet thermal requirements",
            "help_text": "This dimension determines the actual glass size that can be installed in the frame.",
        },
        "renovation_height": {
            "description": "Additional height required for renovation installations.<br><br><strong>Purpose:</strong><br>• Accommodate existing sill heights<br>• Provide proper drainage<br>• Ensure weather sealing<br>• Maintain structural integrity<br><br><strong>Typical Values:</strong><br>• Standard: 38-50mm<br>• High performance: 60-80mm",
            "help_text": "This height ensures proper installation over existing sills while maintaining weather performance.",
        },
        "glazing_undercut_height": {
            "description": "Depth of the undercut in glazing beads for glass installation.<br><br><strong>Function:</strong><br>• Secure glass positioning<br>• Weather seal accommodation<br>• Thermal break continuity<br>• Easy glass replacement<br><br><strong>Standards:</strong><br>• Minimum 3mm for small glass<br>• 5-8mm for larger panes",
            "help_text": "Proper undercut depth ensures secure glass installation and effective weather sealing.",
        },
        "pic": {
            "description": "Reference image or technical drawing for this profile.<br><br><strong>File Types:</strong><br>• Technical drawings (PDF, DWG)<br>• Product photos (JPG, PNG)<br>• Cross-section diagrams<br>• Installation guides<br><br><strong>Benefits:</strong><br>• Visual identification<br>• Installation reference<br>• Quality control<br>• Customer communication",
            "help_text": "Visual references help ensure correct profile selection and proper installation procedures.",
        },
        "sash_overlap": {
            "description": "Overlap dimension between sash and frame components.<br><br><strong>Purpose:</strong><br>• Weather sealing<br>• Structural connection<br>• Thermal performance<br>• Security enhancement<br><br><strong>Typical Values:</strong><br>• Residential: 8-12mm<br>• Commercial: 12-20mm<br>• High performance: 15-25mm",
            "help_text": "Adequate overlap is essential for weather resistance and thermal performance of the window system.",
        },
        "flying_mullion_horizontal_clearance": {
            "description": "Horizontal clearance required for flying mullion installation.<br><br><strong>Purpose:</strong><br>• Thermal expansion accommodation<br>• Installation tolerance<br>• Structural movement<br>• Weather sealing space<br><br><strong>Typical Range:</strong><br>• Standard: 6-10mm<br>• High movement: 12-15mm",
            "help_text": "Proper clearance prevents binding and ensures long-term performance of the mullion system.",
        },
        "flying_mullion_vertical_clearance": {
            "description": "Vertical clearance required for flying mullion installation.<br><br><strong>Considerations:</strong><br>• Building settlement<br>• Thermal movement<br>• Installation accuracy<br>• Maintenance access<br><br><strong>Standards:</strong><br>• Minimum: 40mm<br>• Recommended: 50-60mm",
            "help_text": "Vertical clearance must accommodate building movement and provide access for maintenance and adjustment.",
        },
        "steel_material_thickness": {
            "description": "Thickness of steel reinforcement used in the profile.<br><br><strong>Applications:</strong><br>• Large span windows<br>• High wind load areas<br>• Security requirements<br>• Structural glazing<br><br><strong>Common Thicknesses:</strong><br>• Light duty: 1.5-2.0mm<br>• Standard: 2.0-3.0mm<br>• Heavy duty: 3.0-5.0mm",
            "help_text": "Steel reinforcement thickness must be selected based on structural requirements and local building codes.",
        },
        "reinforcement_steel": {
            "description": "Type and specification of steel reinforcement used.<br><br><strong>Options:</strong><br>• <strong>Standard Steel</strong> - Basic structural support<br>• <strong>High Strength Steel</strong> - Enhanced load capacity<br>• <strong>Galvanized Steel</strong> - Corrosion protection<br><br><strong>Selection Criteria:</strong><br>• Load requirements<br>• Environmental conditions<br>• Durability needs<br>• Cost considerations",
            "help_text": "Choose reinforcement steel based on structural requirements and environmental exposure conditions.",
        },
        "colours": {
            "description": "Available color options for the profile finish.<br><br><strong>Common Options:</strong><br>• <strong>White</strong> - Classic, versatile choice<br>• <strong>Brown</strong> - Traditional, warm appearance<br>• <strong>Black</strong> - Modern, contemporary look<br>• <strong>Grey</strong> - Neutral, sophisticated<br>• <strong>Wood Grain</strong> - Natural appearance<br><br><strong>Considerations:</strong><br>• Architectural style<br>• Maintenance requirements<br>• Heat absorption<br>• Fade resistance",
            "help_text": "Color selection affects both appearance and performance. Darker colors may require special consideration for thermal expansion.",
        },
        "price_per_beam": {
            "description": "Cost per standard length beam of this profile.<br><br><strong>Calculation:</strong><br>• Price per meter × beam length<br>• May include cutting/handling charges<br>• Volume discounts may apply<br><br><strong>Usage:</strong><br>• Project cost estimation<br>• Inventory valuation<br>• Supplier comparison<br>• Quote generation",
            "help_text": "Beam pricing often provides better value than cut-to-length pricing for larger projects.",
        },
        # Add more tooltip content for other fields as needed
    }

    if existing_nodes:
        print(f"  Found {len(existing_nodes)} existing nodes, updating metadata and tooltips...")
        existing_map = {n.name: n for n in existing_nodes}

        updated_count = 0
        for attr_def in attribute_definitions:
            if attr_def["name"] in existing_map:
                node = existing_map[attr_def["name"]]
                node.sort_order = attr_def["sort_order"]
                node.ui_component = attr_def["ui_component"]
                node.validation_rules = attr_def.get("validation_rules")
                node.display_condition = attr_def.get("display_condition")
                
                # Update display_name if provided in definition
                if "display_name" in attr_def:
                    node.display_name = attr_def["display_name"]

                # Update with rich tooltip content if available
                if attr_def["name"] in tooltip_content:
                    node.description = tooltip_content[attr_def["name"]]["description"]
                    node.help_text = tooltip_content[attr_def["name"]]["help_text"]
                else:
                    node.description = attr_def["description"]
                    node.help_text = attr_def["help_text"]

                updated_count += 1

        await session.commit()
        print(f"  Updated {updated_count} attribute nodes with tooltips")

        # Now create option nodes for dropdown fields
        print("Creating option nodes for dropdown fields...")
        for attr_def in attribute_definitions:
            if "options" in attr_def and attr_def["name"] in existing_map:
                parent_node = existing_map[attr_def["name"]]
                await create_option_nodes_for_field(session, parent_node, attr_def["options"])

        return

    # Create attribute nodes if not existing
    created_count = 0
    created_nodes = {}

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
            display_name=attr_def.get("display_name"),  # Use display_name if provided
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
        created_nodes[attr_def["name"]] = node
        created_count += 1

    await session.commit()
    print(f"  Created {created_count} attribute nodes with comprehensive tooltips")

    # Refresh nodes to get their IDs
    for node in created_nodes.values():
        await session.refresh(node)

    # Now create option nodes for dropdown fields
    print("Creating option nodes for dropdown fields...")
    for attr_def in attribute_definitions:
        if "options" in attr_def:
            parent_node = created_nodes[attr_def["name"]]
            await create_option_nodes_for_field(session, parent_node, attr_def["options"])


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

            # Create attribute nodes with proper option hierarchy
            await create_attribute_nodes(session, manufacturing_type)

        print("\n" + "=" * 70)
        print("Setup completed successfully!")
        print(f"Manufacturing Type ID: {manufacturing_type.id}")
        print(
            "All dropdown fields now have proper option nodes instead of hardcoded validation rules"
        )
        print("Hierarchy is properly structured for conditional field visibility")
        print("You can now use the Entry Page system with this manufacturing type.")

    except Exception as e:
        print(f"\nError during setup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
