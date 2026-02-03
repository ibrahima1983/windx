"""Glazing scope debug script.

This script provides debugging functionality for the glazing scope,
including component inspection and glazing unit validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .base import BaseProductDefinitionDebug
from app.models.attribute_node import AttributeNode
from app.services.product_definition.factory import ProductDefinitionServiceFactory


class GlazingDebug(BaseProductDefinitionDebug):
    """Debug script for glazing scope with compositional structure."""

    def __init__(self):
        super().__init__("glazing")

    async def debug_scope_data(self, db: AsyncSession) -> None:
        """Debug glazing scope data."""
        print(f"  [DEBUG] Debugging {self.scope} scope data...")
        
        # Check scope metadata
        await self._debug_scope_metadata(db)
        
        # Check entity definitions
        await self._debug_entity_definitions(db)
        
        # Check component counts
        await self._debug_component_counts(db)
        
        # Check glazing units
        await self._debug_glazing_units(db)
        
        # Validate component properties
        await self._validate_component_properties(db)

    async def _debug_scope_metadata(self, db: AsyncSession) -> None:
        """Debug scope metadata."""
        print(f"    [METADATA] Checking scope metadata...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type == "scope_metadata"
        )
        result = await db.execute(stmt)
        metadata_nodes = result.scalars().all()
        
        if not metadata_nodes:
            print(f"       ❌ No scope metadata found for {self.scope}")
            return
        
        for node in metadata_nodes:
            print(f"       ✅ Scope metadata found (ID: {node.id})")
            print(f"          Name: {node.name}")
            print(f"          Display Name: {node.display_name}")
            print(f"          LTREE Path: {node.ltree_path}")
            
            if node.metadata_:
                entities = node.metadata_.get("entities", {})
                glazing_types = node.metadata_.get("glazing_types", [])
                print(f"          Entity types: {len(entities)}")
                for entity_type, config in entities.items():
                    print(f"            - {entity_type}: {config.get('label', entity_type)}")
                print(f"          Glazing types: {', '.join(glazing_types)}")

    async def _debug_entity_definitions(self, db: AsyncSession) -> None:
        """Debug entity definitions."""
        print(f"    [ENTITIES] Checking entity definitions...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type == "entity_definition"
        )
        result = await db.execute(stmt)
        entity_nodes = result.scalars().all()
        
        if not entity_nodes:
            print(f"       ❌ No entity definitions found for {self.scope}")
            return
        
        print(f"       ✅ Found {len(entity_nodes)} entity definitions:")
        for node in entity_nodes:
            entity_type = node.metadata_.get("entity_type") if node.metadata_ else "unknown"
            metadata_fields = node.metadata_.get("metadata_fields", []) if node.metadata_ else []
            print(f"          - {entity_type}: {node.display_name} (ID: {node.id})")
            print(f"            Metadata fields: {len(metadata_fields)}")

    async def _debug_component_counts(self, db: AsyncSession) -> None:
        """Debug component counts by type."""
        print(f"    [COUNTS] Checking component counts...")
        
        # Define expected component types
        component_types = ["glass_type", "spacer", "gas"]
        
        for component_type in component_types:
            stmt = select(func.count(AttributeNode.id)).where(
                AttributeNode.page_type == self.scope,
                AttributeNode.node_type == component_type
            )
            result = await db.execute(stmt)
            count = result.scalar()
            
            print(f"       {component_type}: {count} components")
            
            # Show sample components
            if count > 0:
                sample_stmt = select(AttributeNode).where(
                    AttributeNode.page_type == self.scope,
                    AttributeNode.node_type == component_type
                ).limit(3)
                sample_result = await db.execute(sample_stmt)
                samples = sample_result.scalars().all()
                
                for sample in samples:
                    print(f"         - {sample.name}")

    async def _debug_glazing_units(self, db: AsyncSession) -> None:
        """Debug glazing units."""
        print(f"    [UNITS] Checking glazing units...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type == "glazing_unit"
        )
        result = await db.execute(stmt)
        unit_nodes = result.scalars().all()
        
        if not unit_nodes:
            print(f"       ⚠️  No glazing units found")
            return
        
        print(f"       ✅ Found {len(unit_nodes)} glazing units:")
        for node in unit_nodes:
            if node.metadata_:
                glazing_type = node.metadata_.get("glazing_type", "unknown")
                u_value = node.metadata_.get("u_value", "N/A")
                thickness = node.metadata_.get("total_thickness", "N/A")
                print(f"          - {node.name} ({glazing_type})")
                print(f"            U-value: {u_value}, Thickness: {thickness}mm")

    async def _validate_component_properties(self, db: AsyncSession) -> None:
        """Validate component properties."""
        print(f"    [VALIDATION] Validating component properties...")
        
        # Check glass types
        await self._validate_glass_properties(db)
        
        # Check spacers
        await self._validate_spacer_properties(db)
        
        # Check gases
        await self._validate_gas_properties(db)

    async def _validate_glass_properties(self, db: AsyncSession) -> None:
        """Validate glass type properties."""
        print(f"      [GLASS] Validating glass properties...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type == "glass_type"
        )
        result = await db.execute(stmt)
        glass_nodes = result.scalars().all()
        
        issues = 0
        for node in glass_nodes:
            if not node.metadata_:
                issues += 1
                print(f"         ❌ {node.name}: No metadata")
                continue
            
            metadata = node.metadata_
            
            # Check required properties
            required_props = ["thickness", "u_value"]
            for prop in required_props:
                if prop not in metadata or metadata[prop] is None:
                    issues += 1
                    print(f"         ❌ {node.name}: Missing {prop}")
            
            # Check value ranges
            if "u_value" in metadata and metadata["u_value"]:
                u_value = float(metadata["u_value"])
                if u_value < 0 or u_value > 10:
                    issues += 1
                    print(f"         ⚠️  {node.name}: Unusual U-value: {u_value}")
            
            if "light_transmittance" in metadata and metadata["light_transmittance"]:
                lt = float(metadata["light_transmittance"])
                if lt < 0 or lt > 100:
                    issues += 1
                    print(f"         ❌ {node.name}: Invalid light transmittance: {lt}%")
        
        if issues == 0:
            print(f"         ✅ All glass properties are valid")
        else:
            print(f"         ⚠️  Found {issues} property issues")

    async def _validate_spacer_properties(self, db: AsyncSession) -> None:
        """Validate spacer properties."""
        print(f"      [SPACER] Validating spacer properties...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type == "spacer"
        )
        result = await db.execute(stmt)
        spacer_nodes = result.scalars().all()
        
        issues = 0
        for node in spacer_nodes:
            if not node.metadata_:
                issues += 1
                print(f"         ❌ {node.name}: No metadata")
                continue
            
            metadata = node.metadata_
            
            # Check required properties
            required_props = ["material", "width"]
            for prop in required_props:
                if prop not in metadata or metadata[prop] is None:
                    issues += 1
                    print(f"         ❌ {node.name}: Missing {prop}")
            
            # Check width range
            if "width" in metadata and metadata["width"]:
                width = float(metadata["width"])
                if width < 6 or width > 30:
                    issues += 1
                    print(f"         ⚠️  {node.name}: Unusual width: {width}mm")
        
        if issues == 0:
            print(f"         ✅ All spacer properties are valid")
        else:
            print(f"         ⚠️  Found {issues} property issues")

    async def _validate_gas_properties(self, db: AsyncSession) -> None:
        """Validate gas properties."""
        print(f"      [GAS] Validating gas properties...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type == "gas"
        )
        result = await db.execute(stmt)
        gas_nodes = result.scalars().all()
        
        issues = 0
        for node in gas_nodes:
            if not node.metadata_:
                issues += 1
                print(f"         ❌ {node.name}: No metadata")
                continue
            
            metadata = node.metadata_
            
            # Check density range
            if "density" in metadata and metadata["density"]:
                density = float(metadata["density"])
                if density < 0.5 or density > 10:
                    issues += 1
                    print(f"         ⚠️  {node.name}: Unusual density: {density} kg/m³")
            
            # Check thermal conductivity
            if "thermal_conductivity" in metadata and metadata["thermal_conductivity"]:
                tc = float(metadata["thermal_conductivity"])
                if tc < 0.005 or tc > 0.05:
                    issues += 1
                    print(f"         ⚠️  {node.name}: Unusual thermal conductivity: {tc} W/mK")
        
        if issues == 0:
            print(f"         ✅ All gas properties are valid")
        else:
            print(f"         ⚠️  Found {issues} property issues")


# Script execution
if __name__ == "__main__":
    from .base import run_async_script
    
    async def main():
        debug = GlazingDebug()
        await debug.run_debug()
    
    run_async_script(main())