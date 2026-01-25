"""Repository for AttributeNode operations with hierarchy support.

This module provides the repository implementation for AttributeNode
model with hierarchical query methods using LTREE.

Public Classes:
    AttributeNodeRepository: Repository for attribute node operations

Features:
    - Hierarchical queries via HierarchicalRepository
    - Get by manufacturing type
    - Get root nodes
    - LTREE pattern matching
    - Efficient tree traversal
    - Tree building utilities
"""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.repositories.windx_base import HierarchicalRepository
from app.schemas.attribute_node import (
    AttributeNodeCreate,
    AttributeNodeTree,
    AttributeNodeUpdate,
)

__all__ = ["AttributeNodeRepository"]


# noinspection PyTypeChecker
class AttributeNodeRepository(
    HierarchicalRepository[AttributeNode, AttributeNodeCreate, AttributeNodeUpdate]
):
    """Repository for AttributeNode operations with hierarchy support.

    Extends HierarchicalRepository to provide LTREE-based hierarchical
    queries for attribute nodes. Includes methods for filtering by
    manufacturing type and pattern matching.


    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with AttributeNode model.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(AttributeNode, db)

    async def get_by_manufacturing_type(self, manufacturing_type_id: int) -> list[AttributeNode]:
        """Get all attribute nodes for a manufacturing type.

        Returns all nodes in the attribute tree for the specified
        manufacturing type, ordered by ltree_path for hierarchical display.

        Args:
            manufacturing_type_id (int): Manufacturing type ID

        Returns:
            list[AttributeNode]: List of attribute nodes ordered by path

        Example:
            ```python
            # Get all attributes for Window type
            window_attrs = await repo.get_by_manufacturing_type(1)
            ```
        """
        # noinspection PyTypeChecker
        result = await self.db.execute(
            select(AttributeNode)
            .where(AttributeNode.manufacturing_type_id == manufacturing_type_id)
            .order_by(AttributeNode.ltree_path)
        )
        return list(result.scalars().all())

    async def get_root_nodes(self, manufacturing_type_id: int | None = None) -> list[AttributeNode]:
        """Get root nodes (top-level nodes with no parent).

        Returns nodes at the top of the hierarchy. Can optionally filter
        by manufacturing type.

        Args:
            manufacturing_type_id (int | None): Optional manufacturing type filter

        Returns:
            list[AttributeNode]: List of root nodes ordered by sort_order and name

        Example:
            ```python
            # Get all root nodes
            roots = await repo.get_root_nodes()

            # Get root nodes for specific manufacturing type
            window_roots = await repo.get_root_nodes(manufacturing_type_id=1)
            ```
        """
        query = select(AttributeNode).where(AttributeNode.parent_node_id.is_(None))

        if manufacturing_type_id is not None:
            query = query.where(AttributeNode.manufacturing_type_id == manufacturing_type_id)

        query = query.order_by(AttributeNode.sort_order, AttributeNode.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_by_path_pattern(self, pattern: str) -> list[AttributeNode]:
        """Search attribute nodes using LTREE lquery pattern.

        Uses PostgreSQL LTREE lquery syntax for pattern matching.
        Supports wildcards and complex path patterns.

        Args:
            pattern (str): LTREE lquery pattern

        Returns:
            list[AttributeNode]: List of matching nodes ordered by path

        Example:
            ```python
            # Find all nodes with 'material' in path
            materials = await repo.search_by_path_pattern('*.material.*')

            # Find nodes at specific depth (3 levels)
            level3 = await repo.search_by_path_pattern('*{3}')

            # Find specific path pattern
            frames = await repo.search_by_path_pattern('window.frame.*')
            ```

        Pattern Syntax:
            - `*`: Match any single label
            - `*{n}`: Match exactly n labels
            - `*{n,}`: Match n or more labels
            - `*{,n}`: Match up to n labels
            - `*{n,m}`: Match between n and m labels
            - `label1|label2`: Match either label1 or label2
        """
        result = await self.db.execute(
            select(AttributeNode)
            .where(AttributeNode.ltree_path.lquery(pattern))
            .order_by(AttributeNode.ltree_path)
        )
        return list(result.scalars().all())

    @staticmethod
    def get_filtered(
        manufacturing_type_id: int | None = None,
        parent_node_id: int | None = None,
        node_type: str | None = None,
    ) -> Select:
        """Build filtered query for attribute nodes.

        Creates a SQLAlchemy Select statement with optional filters.
        This method returns a query that can be paginated.

        Args:
            manufacturing_type_id (int | None): Filter by manufacturing type
            parent_node_id (int | None): Filter by parent node
            node_type (str | None): Filter by node type

        Returns:
            Select: SQLAlchemy select statement

        Example:
            ```python
            query = repo.get_filtered(
                manufacturing_type_id=1,
                node_type="option"
            )
            result = await db.execute(query)
            nodes = result.scalars().all()
            ```
        """
        query = select(AttributeNode)

        # Apply filters
        if manufacturing_type_id is not None:
            query = query.where(AttributeNode.manufacturing_type_id == manufacturing_type_id)

        if parent_node_id is not None:
            query = query.where(AttributeNode.parent_node_id == parent_node_id)
        elif parent_node_id is None and "parent_node_id" in locals():
            # Explicitly filter for root nodes if parent_node_id is None
            query = query.where(AttributeNode.parent_node_id.is_(None))

        if node_type:
            query = query.where(AttributeNode.node_type == node_type)

        # Order by ltree_path for hierarchical display
        query = query.order_by(AttributeNode.ltree_path)

        return query

    @staticmethod
    def build_tree(nodes: list[AttributeNode]) -> list[AttributeNodeTree]:
        """Build hierarchical tree structure from flat list of nodes.

        Converts a flat list of attribute nodes into a nested tree structure
        based on parent-child relationships.

        Args:
            nodes (list[AttributeNode]): Flat list of nodes

        Returns:
            list[AttributeNodeTree]: Hierarchical tree structure

        Example:
            ```python
            # Get all nodes for a manufacturing type
            nodes = await repo.get_by_manufacturing_type(1)

            # Build tree structure
            tree = repo.build_tree(nodes)
            ```

        Note:
            - Nodes should be ordered by ltree_path for optimal performance
            - Root nodes (parent_node_id is None) become top-level items
            - Children are nested under their parents recursively
        """
        # Create a mapping of node_id to node with children list
        node_map: dict[int, AttributeNodeTree] = {}

        for node in nodes:
            node_tree = AttributeNodeTree(
                id=node.id,
                manufacturing_type_id=node.manufacturing_type_id,
                parent_node_id=node.parent_node_id,
                name=node.name,
                node_type=node.node_type,
                data_type=node.data_type,
                display_condition=node.display_condition,
                validation_rules=node.validation_rules,
                required=node.required,
                price_impact_type=node.price_impact_type,
                price_impact_value=node.price_impact_value,
                price_formula=node.price_formula,
                weight_impact=node.weight_impact,
                weight_formula=node.weight_formula,
                technical_property_type=node.technical_property_type,
                technical_impact_formula=node.technical_impact_formula,
                ltree_path=node.ltree_path,
                depth=node.depth,
                sort_order=node.sort_order,
                ui_component=node.ui_component,
                description=node.description,
                help_text=node.help_text,
                created_at=node.created_at,
                updated_at=node.updated_at,
                children=[],
            )
            node_map[node.id] = node_tree

        # Build tree by linking children to parents
        root_nodes: list[AttributeNodeTree] = []

        for node in nodes:
            node_tree = node_map[node.id]

            if node.parent_node_id is None:
                # Root node
                root_nodes.append(node_tree)
            elif node.parent_node_id in node_map:
                # Add to parent's children
                parent = node_map[node.parent_node_id]
                parent.children.append(node_tree)

        return root_nodes

    async def get_with_children(self, node_id: int) -> AttributeNode | None:
        """Get attribute node with immediate children eager-loaded.

        Loads the node along with its direct children in a single query
        to prevent N+1 query problems.

        Args:
            node_id (int): Attribute node ID

        Returns:
            AttributeNode | None: Node with children or None if not found

        Example:
            ```python
            # Get node with children loaded
            node = await repo.get_with_children(42)
            if node:
                for child in node.children:
                    print(f"Child: {child.name}")
            ```
        """
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(AttributeNode)
            .where(AttributeNode.id == node_id)
            .options(selectinload(AttributeNode.children))
        )
        return result.scalar_one_or_none()

    async def get_with_full_tree(self, node_id: int) -> AttributeNode | None:
        """Get attribute node with full subtree eager-loaded.

        Loads the node along with all descendants (children, grandchildren, etc.)
        in optimized queries to prevent N+1 problems.

        Args:
            node_id (int): Attribute node ID

        Returns:
            AttributeNode | None: Node with full subtree or None if not found

        Example:
            ```python
            # Get node with entire subtree loaded
            node = await repo.get_with_full_tree(42)
            if node:
                descendants = await repo.get_descendants(node.id)
                print(f"Total descendants: {len(descendants)}")
            ```
        """
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(AttributeNode)
            .where(AttributeNode.id == node_id)
            .options(selectinload(AttributeNode.children).selectinload(AttributeNode.children))
        )
        return result.scalar_one_or_none()

    async def would_create_cycle(self, node_id: int, new_parent_id: int) -> bool:
        """Check if setting a new parent would create a cycle.

        Validates that moving a node to a new parent would not create
        a circular reference in the hierarchy.

        Args:
            node_id (int): Node to be moved
            new_parent_id (int): Proposed new parent ID

        Returns:
            bool: True if cycle would be created, False otherwise

        Example:
            ```python
            # Check if moving node 5 under node 10 would create cycle
            has_cycle = await repo.would_create_cycle(5, 10)
            if has_cycle:
                raise InvalidHierarchyException("Cannot create cycle")
            ```

        Note:
            A cycle occurs when a node becomes its own ancestor.
            For example: A → B → C → A (cycle)
        """
        # A node cannot be its own parent
        if node_id == new_parent_id:
            return True

        # Get the proposed parent node
        parent = await self.get(new_parent_id)
        if not parent:
            return False  # Parent doesn't exist, no cycle

        # Check if the node is an ancestor of the proposed parent
        # If the parent's path contains the node, it would create a cycle
        node = await self.get(node_id)
        if not node:
            return False  # Node doesn't exist, no cycle

        # Check if parent's ltree_path starts with node's ltree_path
        # This means the parent is a descendant of the node
        if parent.ltree_path.startswith(node.ltree_path + "."):
            return True

        return False
