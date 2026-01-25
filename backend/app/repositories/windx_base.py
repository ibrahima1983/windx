"""Base repository for hierarchical data with LTREE support.

This module provides a specialized repository class for hierarchical data
using PostgreSQL LTREE extension for efficient tree traversal.

Public Classes:
    HierarchicalRepository: Extended repository with LTREE operations

Features:
    - LTREE-based hierarchical queries
    - Descendant and ancestor lookups
    - Direct children queries
    - Full tree structure retrieval
    - O(log n) performance with GiST indexes
"""

from __future__ import annotations

from typing import Generic

from sqlalchemy import select

from app.repositories.base import (
    BaseRepository,
    CreateSchemaType,
    ModelType,
    UpdateSchemaType,
)

__all__ = ["HierarchicalRepository"]


class HierarchicalRepository(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType],
    BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType],
):
    """Extended repository for hierarchical data with LTREE support.

    Provides methods for efficient hierarchical queries using PostgreSQL
    LTREE extension. Assumes the model has ltree_path column.

    Attributes:
        model: SQLAlchemy model class with ltree_path column
        db: Database session
    """

    async def get_descendants(self, node_id: int) -> list[ModelType]:
        """Get all descendants of a node using LTREE.

        Uses the PostgreSQL <@ operator (descendant_of) for efficient
        hierarchical queries. Returns all nodes below the specified node
        in the tree, ordered by path.

        Args:
            node_id (int): ID of the parent node

        Returns:
            list[ModelType]: List of descendant nodes ordered by ltree_path

        Example:
            ```python
            # Get all descendants of node 42
            descendants = await repo.get_descendants(42)
            # Returns all nodes under node 42 in the hierarchy
            ```
        """
        # First get the node to retrieve its path
        node = await self.get(node_id)
        if not node:
            return []

        # Use LTREE descendant_of operator (<@)
        # This finds all nodes whose path is contained by the parent path
        result = await self.db.execute(
            select(self.model)
            .where(self.model.ltree_path.descendant_of(node.ltree_path))
            .where(self.model.id != node_id)  # Exclude the node itself
            .order_by(self.model.ltree_path)
        )
        return list(result.scalars().all())

    async def get_ancestors(self, node_id: int) -> list[ModelType]:
        """Get all ancestors of a node using LTREE.

        Uses the PostgreSQL @> operator (ancestor_of) for efficient
        hierarchical queries. Returns all nodes above the specified node
        in the tree, ordered by path.

        Args:
            node_id (int): ID of the child node

        Returns:
            list[ModelType]: List of ancestor nodes ordered by ltree_path

        Example:
            ```python
            # Get all ancestors of node 42
            ancestors = await repo.get_ancestors(42)
            # Returns all parent nodes up to the root
            ```
        """
        # First get the node to retrieve its path
        node = await self.get(node_id)
        if not node:
            return []

        # Use LTREE ancestor_of operator (@>)
        # This finds all nodes whose path contains the child path
        result = await self.db.execute(
            select(self.model)
            .where(self.model.ltree_path.ancestor_of(node.ltree_path))
            .where(self.model.id != node_id)  # Exclude the node itself
            .order_by(self.model.ltree_path)
        )
        return list(result.scalars().all())

    async def get_children(self, parent_id: int | None) -> list[ModelType]:
        """Get direct children of a node.

        Returns only the immediate children (one level down) of the
        specified parent node. Uses parent_node_id for simple adjacency
        list query.

        Args:
            parent_id (int | None): ID of the parent node, or None for root nodes

        Returns:
            list[ModelType]: List of child nodes ordered by sort_order and name

        Example:
            ```python
            # Get direct children of node 42
            children = await repo.get_children(42)

            # Get root nodes (no parent)
            roots = await repo.get_children(None)
            ```
        """
        # Query for direct children using parent_node_id
        query = select(self.model).where(self.model.parent_node_id == parent_id)

        # Order by sort_order if available, then by name
        if hasattr(self.model, "sort_order"):
            query = query.order_by(self.model.sort_order)
        if hasattr(self.model, "name"):
            query = query.order_by(self.model.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tree(self, root_id: int | None = None) -> list[ModelType]:
        """Get entire tree structure or subtree.

        Returns all nodes in the tree (or subtree if root_id is specified),
        ordered by ltree_path for hierarchical display.

        Args:
            root_id (int | None): ID of the root node for subtree, or None for entire tree

        Returns:
            list[ModelType]: List of all nodes in tree order

        Example:
            ```python
            # Get entire tree
            all_nodes = await repo.get_tree()

            # Get subtree starting from node 42
            subtree = await repo.get_tree(root_id=42)
            ```
        """
        if root_id is not None:
            # Get subtree starting from specified root
            return await self.get_descendants(root_id)

        # Get entire tree ordered by ltree_path
        result = await self.db.execute(select(self.model).order_by(self.model.ltree_path))
        return list(result.scalars().all())
