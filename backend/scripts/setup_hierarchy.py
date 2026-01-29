#!/usr/bin/env python3
"""Unified setup script for creating manufacturing types and attribute hierarchies from YAML configuration.

This script replaces the individual setup scripts (setup_profile_hierarchy.py, 
setup_accessories_hierarchy.py, setup_glazing_hierarchy.py) with a single,
configurable script that reads YAML configuration files.

Usage:
    python setup_hierarchy.py                    # Setup all pages
    python setup_hierarchy.py profile            # Setup profile page only
    python setup_hierarchy.py accessories        # Setup accessories page only
    python setup_hierarchy.py glazing            # Setup glazing page only
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

# Fix Windows CMD encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_engine, get_session_maker
from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType


class HierarchySetup:
    """Unified hierarchy setup class for creating manufacturing types and attributes from YAML."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def setup_from_yaml_file(self, yaml_file: Path) -> None:
        """Setup hierarchy from a YAML configuration file."""
        print(f"Setting up hierarchy from {yaml_file.name}...")
        
        # Load YAML configuration
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"  [ERROR] Error loading YAML file: {e}")
            raise

        # Validate required fields
        required_fields = ['page_type', 'manufacturing_type', 'attributes']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in {yaml_file.name}")

        page_type = config['page_type']
        manufacturing_type_name = config['manufacturing_type']
        
        print(f"  [PAGE] Page Type: {page_type}")
        print(f"  [MFG] Manufacturing Type: {manufacturing_type_name}")

        # Validate configuration for potential case-sensitivity issues
        self.validate_configuration(config, yaml_file.name)

        # Get or create manufacturing type
        manufacturing_type = await self.get_or_create_manufacturing_type(
            manufacturing_type_name, 
            config.get('manufacturing_type_config', {})
        )

        # Create attributes from configuration
        await self.create_attributes_from_config(
            manufacturing_type, 
            page_type, 
            config['attributes']
        )

    def validate_configuration(self, config: Dict[str, Any], filename: str) -> None:
        """Validate configuration for potential issues and inconsistencies."""
        print(f"  [VALIDATE] Validating configuration for potential issues...")
        
        # Collect all option values and display condition values
        option_values = set()
        display_condition_values = set()
        
        for attr in config.get('attributes', []):
            # Collect option values
            if 'options' in attr:
                for option in attr['options']:
                    normalized = self.normalize_option_value(option)
                    option_values.add(normalized)
            
            # Collect display condition values
            if 'display_condition' in attr:
                condition_values = self.extract_condition_values(attr['display_condition'])
                display_condition_values.update(condition_values)
        
        # Check for potential mismatches
        mismatches = display_condition_values - option_values
        if mismatches:
            print(f"  [WARNING] Potential case-sensitivity issues in {filename}:")
            for mismatch in mismatches:
                print(f"    - Display condition value '{mismatch}' may not match any option")
                # Try to find similar values
                for option in option_values:
                    if mismatch.lower() == option.lower() and mismatch != option:
                        print(f"      Did you mean '{option}' instead of '{mismatch}'?")
        else:
            print(f"  [OK] No case-sensitivity issues detected")

    def extract_condition_values(self, condition: Dict[str, Any]) -> set:
        """Extract all values from display conditions recursively."""
        values = set()
        
        if not condition:
            return values
            
        # Handle single condition
        if 'value' in condition and isinstance(condition['value'], str):
            values.add(self.normalize_option_value(condition['value']))
        
        # Handle nested conditions (AND/OR)
        if 'conditions' in condition:
            for cond in condition['conditions']:
                values.update(self.extract_condition_values(cond))
        
        # Handle single nested condition (NOT)
        if 'condition' in condition:
            values.update(self.extract_condition_values(condition['condition']))
            
        return values

    async def get_or_create_manufacturing_type(
        self, 
        name: str, 
        config: Dict[str, Any]
    ) -> ManufacturingType:
        """Get existing or create new manufacturing type."""
        print(f"  [SEARCH] Getting manufacturing type: {name}")

        # Check if it already exists
        stmt = select(ManufacturingType).where(ManufacturingType.name == name)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"    [OK] Using existing manufacturing type (ID: {existing.id})")
            return existing

        # Create new manufacturing type
        manufacturing_type = ManufacturingType(
            name=name,
            description=config.get('description', f"{name} system"),
            base_category=config.get('base_category', 'window'),
            base_price=Decimal(str(config.get('base_price', 200.00))),
            base_weight=Decimal(str(config.get('base_weight', 15.00))),
            is_active=True,
        )

        self.session.add(manufacturing_type)
        await self.session.commit()
        await self.session.refresh(manufacturing_type)

        print(f"    [OK] Created manufacturing type (ID: {manufacturing_type.id})")
        return manufacturing_type

    async def create_attributes_from_config(
        self, 
        manufacturing_type: ManufacturingType, 
        page_type: str, 
        attributes: List[Dict[str, Any]]
    ) -> None:
        """Create attribute nodes from configuration."""
        print(f"  [CREATE] Creating {len(attributes)} attribute nodes for {page_type}...")

        # Check if attributes already exist for this page type
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == page_type,
        )
        result = await self.session.execute(stmt)
        existing_nodes = result.scalars().all()

        if existing_nodes:
            print(f"    [DELETE] Found {len(existing_nodes)} existing {page_type} nodes, deleting them...")
            # Delete existing nodes to recreate with updated configuration
            from sqlalchemy import delete
            delete_stmt = delete(AttributeNode).where(
                AttributeNode.manufacturing_type_id == manufacturing_type.id,
                AttributeNode.page_type == page_type,
            )
            await self.session.execute(delete_stmt)
            await self.session.commit()
            print(f"    [DELETE] Deleted existing {page_type} nodes")

        # Create attribute nodes
        created_count = 0
        for attr_config in attributes:
            await self.create_attribute_node(manufacturing_type.id, page_type, attr_config)
            created_count += 1

        await self.session.commit()
        print(f"    [OK] Created {created_count} attribute nodes")

    async def create_attribute_node(
        self, 
        manufacturing_type_id: int, 
        page_type: str, 
        config: Dict[str, Any]
    ) -> AttributeNode:
        """Create a single attribute node from configuration."""
        # Extract required fields
        name = config['name']
        description = config.get('description', '')
        node_type = config.get('node_type', 'attribute')
        data_type = config.get('data_type', 'string')
        required = config.get('required', False)

        # Extract optional fields with defaults
        ltree_path = config.get('ltree_path', f"{page_type}.{name}")
        depth = config.get('depth', 1)
        sort_order = config.get('sort_order', 1)
        ui_component = config.get('ui_component', 'input')
        help_text = config.get('help_text', '')

        # Extract complex fields
        validation_rules = config.get('validation_rules')
        display_condition = config.get('display_condition')
        calculated_field = config.get('calculated_field')
        metadata = config.get('metadata')

        # Normalize display condition values to prevent case-sensitivity issues
        if display_condition:
            display_condition = self.normalize_display_condition(display_condition)

        # Extract pricing and weight impact fields
        price_impact_type = config.get('price_impact_type', 'fixed')
        price_impact_value = config.get('price_impact_value')
        price_formula = config.get('price_formula')
        weight_impact = config.get('weight_impact', 0)
        weight_formula = config.get('weight_formula')
        
        # Extract technical property fields
        technical_property_type = config.get('technical_property_type')
        technical_impact_formula = config.get('technical_impact_formula')

        # Create attribute node
        node = AttributeNode(
            manufacturing_type_id=manufacturing_type_id,
            parent_node_id=None,  # All are root level for now
            name=name,
            display_name=config.get('display_name', name.replace('_', ' ').title()),
            description=description,
            node_type=node_type,
            data_type=data_type,
            required=required,
            ltree_path=ltree_path,
            depth=depth,
            sort_order=sort_order,
            ui_component=ui_component,
            help_text=help_text,
            validation_rules=validation_rules,
            display_condition=display_condition,
            calculated_field=calculated_field,
            metadata_=metadata,
            page_type=page_type,
            # Add pricing and weight impact fields
            price_impact_type=price_impact_type,
            price_impact_value=Decimal(str(price_impact_value)) if price_impact_value is not None else None,
            price_formula=price_formula,
            weight_impact=Decimal(str(weight_impact)),
            weight_formula=weight_formula,
            # Add technical property fields
            technical_property_type=technical_property_type,
            technical_impact_formula=technical_impact_formula,
        )

        self.session.add(node)

        # Create option nodes if validation_rules contains options OR if options are defined directly
        options_list = None
        if validation_rules and 'options' in validation_rules:
            options_list = validation_rules['options']
            print(f"    [DEBUG] Found options in validation_rules for {name}: {len(options_list)} options")
        elif 'options' in config:
            options_list = config['options']
            print(f"    [DEBUG] Found direct options for {name}: {len(options_list)} options")
        else:
            print(f"    [DEBUG] No options found for {name}")
        
        if options_list:
            await self.session.flush()  # Ensure node has an ID
            await self.create_option_nodes(node, options_list)

        return node

    def normalize_display_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize display condition values to match option values format.
        
        This prevents case-sensitivity issues between display conditions and option values.
        """
        if not condition:
            return condition
            
        # Create a copy to avoid modifying the original
        normalized = condition.copy()
        
        # Handle single condition
        if 'value' in normalized and isinstance(normalized['value'], str):
            normalized['value'] = self.normalize_option_value(normalized['value'])
            print(f"    [NORMALIZE] Display condition value: {condition['value']} -> {normalized['value']}")
        
        # Handle nested conditions (AND/OR)
        if 'conditions' in normalized:
            normalized['conditions'] = [
                self.normalize_display_condition(cond) for cond in normalized['conditions']
            ]
        
        # Handle single nested condition (NOT)
        if 'condition' in normalized:
            normalized['condition'] = self.normalize_display_condition(normalized['condition'])
            
        return normalized

    async def create_option_nodes(self, parent_node: AttributeNode, options: List[str]) -> None:
        """Create option nodes for dropdown/select attributes."""
        print(f"    [OPTIONS] Creating {len(options)} option nodes for {parent_node.name}")
        
        for i, option_value in enumerate(options):
            option_name = self.normalize_option_value(option_value)
            option_node = AttributeNode(
                manufacturing_type_id=parent_node.manufacturing_type_id,
                parent_node_id=parent_node.id,
                name=option_name,
                display_name=option_value,
                description=f"Option: {option_value}",
                node_type="option",
                data_type="string",
                required=False,
                ltree_path=f"{parent_node.ltree_path}.{option_name}",
                depth=parent_node.depth + 1,
                sort_order=i + 1,
                ui_component="option",
                page_type=parent_node.page_type,
            )
            self.session.add(option_node)
            print(f"      [OPTION] Created: {option_value} -> {option_name}")
        
        print(f"    [OPTIONS] Completed creating options for {parent_node.name}")

    def normalize_option_value(self, option_value: str) -> str:
        """Normalize option values to consistent format for database storage and comparison.
        
        This prevents case-sensitivity issues between option values and display conditions.
        """
        return option_value.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')


async def setup_page(page_type: str) -> None:
    """Setup a specific page type from its YAML configuration."""
    config_dir = Path(__file__).parent.parent / "config" / "pages"
    yaml_file = config_dir / f"{page_type}.yaml"
    
    if not yaml_file.exists():
        print(f"[ERROR] Configuration file not found: {yaml_file}")
        return False

    engine = get_engine()
    session_maker = get_session_maker()

    try:
        async with session_maker() as session:
            setup = HierarchySetup(session)
            await setup.setup_from_yaml_file(yaml_file)
        
        print(f"[OK] {page_type.title()} setup completed successfully!")
        return True

    except Exception as e:
        print(f"[ERROR] Error during {page_type} setup: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def setup_all_pages() -> None:
    """Setup all available page types."""
    config_dir = Path(__file__).parent.parent / "config" / "pages"
    
    if not config_dir.exists():
        print(f"[ERROR] Configuration directory not found: {config_dir}")
        return

    # Find all YAML files in the config directory
    yaml_files = list(config_dir.glob("*.yaml"))
    
    if not yaml_files:
        print(f"[ERROR] No YAML configuration files found in {config_dir}")
        return

    print(f"Found {len(yaml_files)} configuration files:")
    for yaml_file in yaml_files:
        print(f"  [FILE] {yaml_file.name}")

    success_count = 0
    for yaml_file in yaml_files:
        page_type = yaml_file.stem  # filename without extension
        print(f"\n{'='*60}")
        print(f"Setting up {page_type.title()} page...")
        print('='*60)
        
        if await setup_page(page_type):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Setup Summary: {success_count}/{len(yaml_files)} pages completed successfully")
    print('='*60)


async def main():
    """Main setup function."""
    if len(sys.argv) > 1:
        # Setup specific page type
        page_type = sys.argv[1].lower()
        print(f"Setting up {page_type.title()} page hierarchy...")
        print("=" * 60)
        
        success = await setup_page(page_type)
        if not success:
            sys.exit(1)
    else:
        # Setup all pages
        print("Setting up all page hierarchies...")
        print("=" * 60)
        await setup_all_pages()


if __name__ == "__main__":
    asyncio.run(main())