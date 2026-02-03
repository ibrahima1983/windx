"""Profile scope debug script.

This script provides debugging functionality for the profile scope,
including data inspection and relationship validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .base import BaseProductDefinitionDebug
from app.models.attribute_node import AttributeNode
from app.services.product_definition.factory import ProductDefinitionServiceFactory


class ProfileDebug(BaseProductDefinitionDebug):
    """Debug script for profile scope with hierarchical dependencies."""

    def __init__(self):
        super().__init__("profile")

    async def debug_scope_data(self, db: AsyncSession) -> None:
        """Debug profile scope data."""
        print(f"  [DEBUG] Debugging {self.scope} scope data...")
        
        # Check scope metadata
        await self._debug_scope_metadata(db)
        
        # Check entity definitions
        await self._debug_entity_definitions(db)
        
        # Check entity counts
        await self._debug_entity_counts(db)
        
        # Check dependency paths
        await self._debug_dependency_paths(db)
        
        # Validate hierarchy integrity
        await self._validate_hierarchy_integrity(db)

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
                hierarchy = node.metadata_.get("hierarchy", {})
                print(f"          Hierarchy levels: {len(hierarchy)}")
                for level, entity_type in hierarchy.items():
                    print(f"            Level {level}: {entity_type}")

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
            print(f"          - {entity_type}: {node.display_name} (ID: {node.id})")

    async def _debug_entity_counts(self, db: AsyncSession) -> None:
        """Debug entity counts by type."""
        print(f"    [COUNTS] Checking entity counts...")
        
        # Define expected entity types
        entity_types = ["company", "material", "opening_system", "system_series", "color"]
        
        for entity_type in entity_types:
            stmt = select(func.count(AttributeNode.id)).where(
                AttributeNode.page_type == self.scope,
                AttributeNode.node_type == entity_type
            )
            result = await db.execute(stmt)
            count = result.scalar()
            
            print(f"       {entity_type}: {count} entities")

    async def _debug_dependency_paths(self, db: AsyncSession) -> None:
        """Debug dependency paths."""
        print(f"    [PATHS] Checking dependency paths...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type == "dependency_path"
        )
        result = await db.execute(stmt)
        path_nodes = result.scalars().all()
        
        if not path_nodes:
            print(f"       ⚠️  No dependency paths found")
            return
        
        print(f"       ✅ Found {len(path_nodes)} dependency paths:")
        for node in path_nodes:
            print(f"          - {node.ltree_path}")
            if node.metadata_:
                path_data = node.metadata_.get("path_data", {})
                path_str = " → ".join([
                    path_data.get("company_name", "?"),
                    path_data.get("material_name", "?"),
                    path_data.get("opening_system_name", "?"),
                    path_data.get("system_series_name", "?"),
                    path_data.get("color_name", "?")
                ])
                print(f"            Path: {path_str}")

    async def _validate_hierarchy_integrity(self, db: AsyncSession) -> None:
        """Validate hierarchy integrity."""
        print(f"    [INTEGRITY] Validating hierarchy integrity...")
        
        # Check for orphaned nodes
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.parent_node_id.isnot(None)
        )
        result = await db.execute(stmt)
        child_nodes = result.scalars().all()
        
        orphaned_count = 0
        for node in child_nodes:
            # Check if parent exists
            parent_stmt = select(AttributeNode).where(
                AttributeNode.id == node.parent_node_id
            )
            parent_result = await db.execute(parent_stmt)
            parent = parent_result.scalar_one_or_none()
            
            if not parent:
                orphaned_count += 1
                print(f"       ❌ Orphaned node: {node.name} (ID: {node.id})")
        
        if orphaned_count == 0:
            print(f"       ✅ No orphaned nodes found")
        else:
            print(f"       ⚠️  Found {orphaned_count} orphaned nodes")
        
        # Check LTREE path consistency
        await self._validate_ltree_paths(db)

    async def _validate_ltree_paths(self, db: AsyncSession) -> None:
        """Validate LTREE path consistency."""
        print(f"    [LTREE] Validating LTREE path consistency...")
        
        stmt = select(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.ltree_path.isnot(None)
        )
        result = await db.execute(stmt)
        nodes = result.scalars().all()
        
        inconsistent_count = 0
        for node in nodes:
            # Check if depth matches LTREE path depth
            if node.ltree_path:
                path_parts = node.ltree_path.split('.')
                expected_depth = len(path_parts) - 1  # Subtract 1 for root
                
                if node.depth != expected_depth:
                    inconsistent_count += 1
                    print(f"       ❌ Depth mismatch: {node.name}")
                    print(f"          LTREE: {node.ltree_path} (depth: {expected_depth})")
                    print(f"          Node depth: {node.depth}")
        
        if inconsistent_count == 0:
            print(f"       ✅ All LTREE paths are consistent")
        else:
            print(f"       ⚠️  Found {inconsistent_count} inconsistent paths")


# Script execution
if __name__ == "__main__":
    from .base import run_async_script
    
    async def main():
        debug = ProfileDebug()
        await debug.run_debug()
    
    run_async_script(main())