"""HierarchyBuilderService for programmatic hierarchy management.

This module provides a comprehensive service for creating and managing hierarchical
attribute data with automatic LTREE path calculation, depth tracking, and validation.

The HierarchyBuilderService is the primary interface for building product configuration
hierarchies in the Windx system. It handles all the complexity of LTREE path management,
depth calculation, and validation, allowing you to focus on defining your product structure.

Public Classes:
    NodeParams: Base dataclass for common node parameters
    HierarchyBuilderService: Main service for hierarchy management

Key Features:
    - Automatic LTREE path calculation and sanitization
    - Automatic depth calculation for nested hierarchies
    - Manufacturing type creation and management
    - Single node creation with comprehensive validation
    - Batch hierarchy creation from nested dictionaries
    - Tree visualization (ASCII and Pydantic/JSON)
    - Circular reference detection
    - Duplicate name detection at same level
    - Transactional batch operations (all-or-nothing)

Usage Example:
    >>> from app.services.hierarchy_builder import HierarchyBuilderService
    >>> from decimal import Decimal
    >>>
    >>> # Initialize service with database session
    >>> service = HierarchyBuilderService(db_session)
    >>>
    >>> # Create a manufacturing type
    >>> window_type = await service.create_manufacturing_type(
    ...     name="Casement Window",
    ...     description="Energy-efficient casement windows",
    ...     base_price=Decimal("200.00"),
    ...     base_weight=Decimal("15.00")
    ... )
    >>>
    >>> # Create root node
    >>> frame_material = await service.create_node(
    ...     manufacturing_type_id=window_type.id,
    ...     name="Frame Material",
    ...     node_type="category"
    ... )
    >>>
    >>> # Create child node with pricing
    >>> aluminum = await service.create_node(
    ...     manufacturing_type_id=window_type.id,
    ...     name="Aluminum",
    ...     node_type="option",
    ...     parent_node_id=frame_material.id,
    ...     price_impact_value=Decimal("50.00"),
    ...     weight_impact=Decimal("2.0")
    ... )
    >>>
    >>> # Create entire hierarchy from dictionary
    >>> hierarchy = {
    ...     "name": "Glass Type",
    ...     "node_type": "category",
    ...     "children": [
    ...         {
    ...             "name": "Pane Count",
    ...             "node_type": "attribute",
    ...             "children": [
    ...                 {"name": "Single Pane", "node_type": "option"},
    ...                 {"name": "Double Pane", "node_type": "option", "price_impact_value": 80.00}
    ...             ]
    ...         }
    ...     ]
    ... }
    >>> root = await service.create_hierarchy_from_dict(window_type.id, hierarchy)
    >>>
    >>> # Get tree as JSON-serializable Pydantic models
    >>> tree = await service.pydantify(window_type.id)
    >>>
    >>> # Generate ASCII tree visualization
    >>> ascii_tree = await service.asciify(window_type.id)
    >>> print(ascii_tree)

For more examples, see: examples/hierarchy_insertion.py
For dashboard documentation, see: docs/HIERARCHY_ADMIN_DASHBOARD.md
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType
from app.repositories.attribute_node import AttributeNodeRepository
from app.repositories.manufacturing_type import ManufacturingTypeRepository
from app.schemas.attribute_node import AttributeNodeTree
from app.schemas.manufacturing_type import ManufacturingTypeCreate
from app.services.base import BaseService

__all__ = ["NodeParams", "HierarchyBuilderService"]


@dataclass
class NodeParams:
    """Base dataclass for common node parameters.

    This dataclass consolidates common parameters used across node creation
    functions to reduce duplication and ensure consistency.

    Attributes:
        manufacturing_type_id: Manufacturing type ID
        name: Node display name
        node_type: Type of node (category, attribute, option, etc.)
        parent_node_id: Optional parent node ID
        data_type: Optional data type for the node
        display_condition: Optional conditional display logic
        validation_rules: Optional validation rules
        required: Whether the node is required
        price_impact_type: How the node affects price
        price_impact_value: Fixed price adjustment amount
        price_formula: Dynamic price calculation formula
        weight_impact: Fixed weight addition
        weight_formula: Dynamic weight calculation formula
        technical_property_type: Type of technical property
        technical_impact_formula: Technical calculation formula
        sort_order: Display order among siblings
        ui_component: UI control type
        description: Help text for users
        help_text: Additional guidance
    """

    manufacturing_type_id: int
    name: str
    node_type: str
    parent_node_id: int | None = None
    data_type: str | None = None
    display_condition: dict | None = None
    validation_rules: dict | None = None
    required: bool = False
    price_impact_type: str = "fixed"
    price_impact_value: Decimal | None = None
    price_formula: str | None = None
    weight_impact: Decimal = Decimal("0")
    weight_formula: str | None = None
    technical_property_type: str | None = None
    technical_impact_formula: str | None = None
    sort_order: int = 0
    ui_component: str | None = None
    description: str | None = None
    help_text: str | None = None


class HierarchyBuilderService(BaseService):
    """Service for building and managing attribute hierarchies.

    This service provides high-level methods for creating manufacturing types
    and attribute nodes with automatic LTREE path and depth calculation.

    Attributes:
        db: Database session
        mfg_type_repo: ManufacturingTypeRepository instance
        attr_node_repo: AttributeNodeRepository instance
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize HierarchyBuilderService.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.mfg_type_repo = ManufacturingTypeRepository(db)
        self.attr_node_repo = AttributeNodeRepository(db)

    @staticmethod
    def _sanitize_for_ltree(name: str) -> str:
        """Sanitize input string for LTREE path compatibility.

        Performs comprehensive sanitization to ensure the name is valid for
        PostgreSQL LTREE paths. Handles all common edge cases including:
        - Unicode characters (accents, diacritics)
        - Special characters and symbols
        - Multiple consecutive spaces/underscores
        - Leading/trailing whitespace
        - Empty or whitespace-only strings
        - Names starting with numbers
        - Very long names (LTREE label limit: 256 chars)

        Args:
            name: Raw input string to sanitize

        Returns:
            str: Sanitized string safe for LTREE paths

        Raises:
            ValueError: If name is empty or becomes empty after sanitization

        Example:
            >>> service._sanitize_for_ltree("Frame Material")
            'frame_material'

            >>> service._sanitize_for_ltree("Aluminum & Steel (Premium)")
            'aluminum_and_steel_premium'

            >>> service._sanitize_for_ltree("  Multiple   Spaces  ")
            'multiple_spaces'

            >>> service._sanitize_for_ltree("Café-Style Door™")
            'cafe_style_door'

            >>> service._sanitize_for_ltree("100% Pure")
            'n_100_percent_pure'

            >>> service._sanitize_for_ltree("Price: $50-$100")
            'price_dollar_50_dollar_100'
        """
        import re
        import unicodedata

        # Validate input
        if not name or not name.strip():
            raise ValueError("Node name cannot be empty or whitespace-only")

        # Step 1: Normalize unicode characters (remove accents, etc.)
        # NFD = Canonical Decomposition, then filter out combining characters
        normalized = unicodedata.normalize("NFD", name)
        ascii_name = "".join(
            char
            for char in normalized
            if unicodedata.category(char) != "Mn"  # Mn = Mark, Nonspacing
        )

        # Step 2: Convert to lowercase
        sanitized = ascii_name.lower()

        # Step 3: Replace common symbols with words
        # Note: We replace symbols with just the word, not wrapped in underscores
        # The separators step will add underscores where needed
        replacements = {
            "&": "_and_",  # Keep underscores for & since it's typically between words
            "+": "_plus_",
            "%": "_percent_",
            "@": "_at_",
            "#": "_number_",
            "$": "dollar",  # No underscores - let context determine
            "€": "euro",
            "£": "pound",
            "¥": "yen",
            "°": "degree",
            "™": "",
            "®": "",
            "©": "",
            "×": "x",
            "÷": "div",
            "=": "equals",
            "<": "lt",
            ">": "gt",
        }

        for symbol, replacement in replacements.items():
            sanitized = sanitized.replace(symbol, replacement)

        # Step 4: Replace common separators with underscores
        separators = [" ", "-", "/", "\\", "|", ".", ",", ";", ":", "~", "`"]
        for sep in separators:
            sanitized = sanitized.replace(sep, "_")

        # Step 5: Remove parentheses, brackets, quotes (but keep content)
        sanitized = re.sub(r'[(){}\[\]"\']', "_", sanitized)

        # Step 6: Remove any remaining non-alphanumeric characters except underscore
        sanitized = re.sub(r"[^a-z0-9_]", "", sanitized)

        # Step 6.5: Add underscores between letter-number and number-letter transitions
        # This handles cases like "dollar500" -> "dollar_500"
        sanitized = re.sub(r"([a-z])(\d)", r"\1_\2", sanitized)  # letter to digit
        sanitized = re.sub(r"(\d)([a-z])", r"\1_\2", sanitized)  # digit to letter

        # Step 7: Replace multiple consecutive underscores with single underscore
        sanitized = re.sub(r"_+", "_", sanitized)

        # Step 8: Strip leading/trailing underscores
        sanitized = sanitized.strip("_")

        # Step 9: Validate result is not empty
        if not sanitized:
            raise ValueError(
                f"Node name '{name}' becomes empty after sanitization. "
                "Please provide a name with at least one alphanumeric character."
            )

        # Step 10: Enforce LTREE label length limit (256 characters)
        if len(sanitized) > 256:
            # Truncate to 256 characters
            sanitized = sanitized[:256]
            # Remove trailing underscore if truncation created one
            sanitized = sanitized.rstrip("_")

        # Step 11: Ensure it doesn't start with a number (LTREE requirement)
        # This must be done AFTER truncation to ensure the final result is valid
        if sanitized and sanitized[0].isdigit():
            sanitized = f"n_{sanitized}"
            # If adding prefix makes it too long, truncate again
            if len(sanitized) > 256:
                sanitized = sanitized[:256].rstrip("_")

        return sanitized

    def _calculate_ltree_path(self, parent: AttributeNode | None, node_name: str) -> str:
        """Calculate LTREE path for a new node.

        Sanitizes the node name using comprehensive sanitization and constructs
        the LTREE path based on whether the node is a root node or a child node.

        Args:
            parent: Parent node (None for root nodes)
            node_name: Display name of the node

        Returns:
            str: Sanitized LTREE path

        Raises:
            ValueError: If node_name is invalid or becomes empty after sanitization

        Example:
            >>> # Root node
            >>> service._calculate_ltree_path(None, "Frame Material")
            'frame_material'

            >>> # Child node with parent path "frame_material"
            >>> service._calculate_ltree_path(parent, "Aluminum & Steel")
            'frame_material.aluminum_and_steel'

            >>> # Complex name with special characters
            >>> service._calculate_ltree_path(None, "100% Café-Style™")
            'n_100_percent_cafe_style'
        """
        # Use robust sanitization function
        sanitized_name = self._sanitize_for_ltree(node_name)

        if parent is None:
            # Root node - return just the sanitized name
            return sanitized_name
        else:
            # Child node - append to parent's path
            return f"{parent.ltree_path}.{sanitized_name}"

    @staticmethod
    def _calculate_depth(parent: AttributeNode | None) -> int:
        """Calculate depth level for a new node.

        Determines the nesting level of a node in the hierarchy based on
        its parent's depth.

        Args:
            parent: Parent node (None for root nodes)

        Returns:
            int: Depth level (0 for root nodes, parent.depth + 1 for children)

        Example:
            >>> # Root node
            >>> service._calculate_depth(None)
            0

            >>> # Child of root node (depth=0)
            >>> service._calculate_depth(root_node)
            1

            >>> # Grandchild (parent depth=1)
            >>> service._calculate_depth(child_node)
            2
        """
        if parent is None:
            # Root node - depth is 0
            return 0
        else:
            # Child node - depth is parent's depth + 1
            return parent.depth + 1

    async def create_manufacturing_type(
        self,
        name: str,
        description: str | None = None,
        base_category: str | None = None,
        base_price: Decimal = Decimal("0"),
        base_weight: Decimal = Decimal("0"),
    ) -> ManufacturingType:
        """Create a new manufacturing type.

        Creates a manufacturing type that serves as the root for an
        attribute hierarchy.

        Args:
            name: Unique manufacturing type name
            description: Optional detailed description
            base_category: Optional high-level category (e.g., "window", "door")
            base_price: Starting price (default: 0)
            base_weight: Base weight in kg (default: 0)

        Returns:
            ManufacturingType: Created manufacturing type instance

        Raises:
            ConflictException: If name already exists
            DatabaseException: If creation fails

        Example:
            >>> mfg_type = await service.create_manufacturing_type(
            ...     name="Casement Window",
            ...     description="Energy-efficient casement windows",
            ...     base_category="window",
            ...     base_price=Decimal("200.00"),
            ...     base_weight=Decimal("15.00")
            ... )
        """
        # Create schema for validation
        mfg_type_data = ManufacturingTypeCreate(
            name=name,
            description=description,
            base_category=base_category,
            base_price=base_price,
            base_weight=base_weight,
        )

        # Use repository to create
        mfg_type = await self.mfg_type_repo.create(mfg_type_data)
        await self.commit()
        await self.refresh(mfg_type)

        return mfg_type

    async def create_node(
        self,
        manufacturing_type_id: int,
        name: str,
        node_type: str,
        parent_node_id: int | None = None,
        data_type: str | None = None,
        display_condition: dict | None = None,
        validation_rules: dict | None = None,
        required: bool = False,
        price_impact_type: str = "fixed",
        price_impact_value: Decimal | None = None,
        price_formula: str | None = None,
        weight_impact: Decimal = Decimal("0"),
        weight_formula: str | None = None,
        technical_property_type: str | None = None,
        technical_impact_formula: str | None = None,
        sort_order: int = 0,
        ui_component: str | None = None,
        description: str | None = None,
        help_text: str | None = None,
    ) -> AttributeNode:
        """Create a single attribute node with automatic path/depth calculation.

        Creates an attribute node and automatically calculates its LTREE path
        and depth based on its parent node. Performs comprehensive input validation
        and sanitization.

        Args:
            manufacturing_type_id: Manufacturing type ID (must be > 0)
            name: Node display name (cannot be empty)
            node_type: Type of node (category, attribute, option, component, technical_spec)
            parent_node_id: Optional parent node ID (None for root nodes)
            data_type: Optional data type (string, number, boolean, formula, dimension, selection)
            display_condition: Optional conditional display logic (JSONB)
            validation_rules: Optional validation rules (JSONB)
            required: Whether this attribute must be selected
            price_impact_type: How it affects price (fixed, percentage, formula)
            price_impact_value: Fixed price adjustment amount (must be >= 0 if provided)
            price_formula: Dynamic price calculation formula
            weight_impact: Fixed weight addition in kg (must be >= 0)
            weight_formula: Dynamic weight calculation formula
            technical_property_type: Type of technical property
            technical_impact_formula: Technical calculation formula
            sort_order: Display order among siblings
            ui_component: UI control type
            description: Help text for users
            help_text: Additional guidance

        Returns:
            AttributeNode: Created attribute node with calculated path and depth

        Raises:
            ValueError: If input validation fails
            NotFoundException: If parent node or manufacturing type not found
            DatabaseException: If creation fails

        Example:
            >>> # Create root node
            >>> root = await service.create_node(
            ...     manufacturing_type_id=1,
            ...     name="Frame Material",
            ...     node_type="category"
            ... )
            >>> # root.ltree_path == "frame_material"
            >>> # root.depth == 0

            >>> # Create child node
            >>> child = await service.create_node(
            ...     manufacturing_type_id=1,
            ...     name="Aluminum",
            ...     node_type="option",
            ...     parent_node_id=root.id,
            ...     price_impact_value=Decimal("50.00")
            ... )
            >>> # child.ltree_path == "frame_material.aluminum"
            >>> # child.depth == 1
        """
        from app.core.exceptions import NotFoundException

        # Input validation
        if manufacturing_type_id <= 0:
            raise ValueError("manufacturing_type_id must be greater than 0")

        if not name or not name.strip():
            raise ValueError("Node name cannot be empty or whitespace-only")

        if len(name) > 200:
            raise ValueError("Node name cannot exceed 200 characters")

        # Validate node_type
        from app.core.exceptions import ValidationException

        valid_node_types = {"category", "attribute", "option", "component", "technical_spec"}
        if node_type not in valid_node_types:
            raise ValidationException(
                f"Invalid node_type '{node_type}'. Must be one of: {', '.join(valid_node_types)}"
            )

        # Validate data_type if provided
        if data_type is not None:
            valid_data_types = {"string", "number", "boolean", "formula", "dimension", "selection"}
            if data_type not in valid_data_types:
                raise ValueError(
                    f"Invalid data_type '{data_type}'. Must be one of: {', '.join(valid_data_types)}"
                )

        # Validate price_impact_type
        valid_price_types = {"fixed", "percentage", "formula"}
        if price_impact_type not in valid_price_types:
            raise ValueError(
                f"Invalid price_impact_type '{price_impact_type}'. Must be one of: {', '.join(valid_price_types)}"
            )

        # Validate price_impact_value if provided
        if price_impact_value is not None and price_impact_value < 0:
            raise ValueError("price_impact_value cannot be negative")

        # Validate weight_impact
        if weight_impact < 0:
            raise ValueError("weight_impact cannot be negative")

        # Validate sort_order
        if sort_order < 0:
            raise ValueError("sort_order cannot be negative")

        # Validate manufacturing type exists
        mfg_type = await self.mfg_type_repo.get(manufacturing_type_id)
        if mfg_type is None:
            raise NotFoundException(f"Manufacturing type with id {manufacturing_type_id} not found")

        # Fetch parent node if parent_node_id is provided
        parent: AttributeNode | None = None
        if parent_node_id is not None:
            if parent_node_id <= 0:
                raise ValueError("parent_node_id must be greater than 0")

            parent = await self.attr_node_repo.get(parent_node_id)
            if parent is None:
                raise NotFoundException(f"Parent node with id {parent_node_id} not found")

            # Validate parent belongs to same manufacturing type
            if parent.manufacturing_type_id != manufacturing_type_id:
                raise ValueError(
                    f"Parent node belongs to manufacturing type {parent.manufacturing_type_id}, "
                    f"but node is being created for manufacturing type {manufacturing_type_id}"
                )

            # Note: Circular reference detection is not needed for new node creation
            # since a new node cannot be its own ancestor. This validation is only
            # needed when moving existing nodes (see move_node method).

        # Calculate ltree_path using helper method
        ltree_path = self._calculate_ltree_path(parent, name)

        # Calculate depth using helper method
        depth = self._calculate_depth(parent)

        # Check for duplicate names at the same level (same parent)
        from sqlalchemy import select

        from app.core.exceptions import ConflictException

        # Query for siblings with the same name
        siblings_query = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type_id,
            AttributeNode.parent_node_id == parent_node_id,
            AttributeNode.name == name,
        )
        result = await self.attr_node_repo.db.execute(siblings_query)
        existing_sibling = result.scalar_one_or_none()

        if existing_sibling is not None:
            parent_desc = f"parent node {parent_node_id}" if parent_node_id else "root level"
            raise ConflictException(
                f"A node with name '{name}' already exists at {parent_desc} "
                f"in manufacturing type {manufacturing_type_id}"
            )

        # Create AttributeNodeCreate schema with calculated fields
        # We need to create the model directly because we're adding computed fields
        from app.models.attribute_node import AttributeNode as AttributeNodeModel

        node = AttributeNodeModel(
            manufacturing_type_id=manufacturing_type_id,
            parent_node_id=parent_node_id,
            name=name,
            node_type=node_type,
            data_type=data_type,
            display_condition=display_condition,
            validation_rules=validation_rules,
            required=required,
            price_impact_type=price_impact_type,
            price_impact_value=price_impact_value,
            price_formula=price_formula,
            weight_impact=weight_impact,
            weight_formula=weight_formula,
            technical_property_type=technical_property_type,
            technical_impact_formula=technical_impact_formula,
            ltree_path=ltree_path,  # Calculated field
            depth=depth,  # Calculated field
            sort_order=sort_order,
            ui_component=ui_component,
            description=description,
            help_text=help_text,
        )

        # Add to session and commit
        self.attr_node_repo.db.add(node)
        await self.commit()
        await self.refresh(node)

        return node

    async def move_node(
        self,
        node_id: int,
        new_parent_id: int | None,
    ) -> AttributeNode:
        """Move a node to a new parent in the hierarchy.

        Moves an existing attribute node to a new parent, recalculating
        its LTREE path and depth. Validates that the move would not create
        a circular reference.

        Args:
            node_id: ID of the node to move
            new_parent_id: ID of the new parent (None for root level)

        Returns:
            AttributeNode: Updated node with new path and depth

        Raises:
            NotFoundException: If node or new parent not found
            ValidationException: If move would create circular reference
            ValueError: If new parent is in different manufacturing type

        Example:
            >>> # Move node 5 to be a child of node 10
            >>> moved_node = await service.move_node(5, 10)

            >>> # Move node 5 to root level
            >>> moved_node = await service.move_node(5, None)
        """
        from app.core.exceptions import NotFoundException, ValidationException

        # Validate node exists
        node = await self.attr_node_repo.get(node_id)
        if node is None:
            raise NotFoundException(f"Node with id {node_id} not found")

        # If new_parent_id is provided, validate it
        new_parent: AttributeNode | None = None
        if new_parent_id is not None:
            if new_parent_id <= 0:
                raise ValueError("new_parent_id must be greater than 0")

            new_parent = await self.attr_node_repo.get(new_parent_id)
            if new_parent is None:
                raise NotFoundException(f"New parent node with id {new_parent_id} not found")

            # Validate new parent belongs to same manufacturing type
            if new_parent.manufacturing_type_id != node.manufacturing_type_id:
                raise ValueError(
                    f"Cannot move node to parent in different manufacturing type. "
                    f"Node is in type {node.manufacturing_type_id}, "
                    f"parent is in type {new_parent.manufacturing_type_id}"
                )

            # Check for circular reference
            would_cycle = await self.attr_node_repo.would_create_cycle(node_id, new_parent_id)
            if would_cycle:
                raise ValidationException(
                    f"Cannot move node {node_id} under node {new_parent_id}: "
                    "this would create a circular reference in the hierarchy"
                )

        # Calculate new ltree_path and depth
        new_ltree_path = self._calculate_ltree_path(new_parent, node.name)
        new_depth = self._calculate_depth(new_parent)

        # Update node
        node.parent_node_id = new_parent_id
        node.ltree_path = new_ltree_path
        node.depth = new_depth

        # Update all descendants' paths and depths
        descendants = await self.attr_node_repo.get_descendants(node_id)
        for descendant in descendants:
            # Calculate relative path from node to descendant
            old_node_path = node.ltree_path
            descendant_relative_path = descendant.ltree_path[len(old_node_path) + 1 :]

            # Update descendant's path
            descendant.ltree_path = f"{new_ltree_path}.{descendant_relative_path}"

            # Update descendant's depth (add the depth change)
            depth_change = new_depth - node.depth
            descendant.depth += depth_change

        await self.commit()
        await self.refresh(node)

        return node

    async def create_hierarchy_from_dict(
        self,
        manufacturing_type_id: int,
        hierarchy_data: dict,
        parent: AttributeNode | None = None,
        _is_root_call: bool = True,
    ) -> AttributeNode:
        """Create a hierarchy from nested dictionary structure.

        Creates an entire attribute hierarchy from a nested dictionary,
        recursively processing children. This enables batch creation of
        complex hierarchies with a single method call.

        The operation is transactional - either all nodes are created
        successfully, or none are created (all-or-nothing).

        Args:
            manufacturing_type_id: Manufacturing type ID
            hierarchy_data: Dictionary containing node data and optional children
            parent: Optional parent node (None for root level)
            _is_root_call: Internal flag to track root call (do not set manually)

        Returns:
            AttributeNode: The root node of the created hierarchy

        Raises:
            ValueError: If hierarchy_data is invalid or missing required fields
            NotFoundException: If manufacturing type or parent not found
            ConflictException: If duplicate names exist at same level
            DatabaseException: If creation fails (triggers rollback)

        Dictionary Structure:
            {
                "name": "Node Name",  # Required
                "node_type": "category",  # Required
                "data_type": "string",  # Optional
                "price_impact_value": 50.00,  # Optional
                "weight_impact": 2.0,  # Optional
                "description": "Description",  # Optional
                # ... any other node fields ...
                "children": [  # Optional - list of child dictionaries
                    {
                        "name": "Child Node",
                        "node_type": "option",
                        # ... child fields ...
                        "children": [...]  # Nested children
                    }
                ]
            }

        Example:
            >>> hierarchy = {
            ...     "name": "Frame Material",
            ...     "node_type": "category",
            ...     "children": [
            ...         {
            ...             "name": "Material Type",
            ...             "node_type": "attribute",
            ...             "data_type": "selection",
            ...             "children": [
            ...                 {
            ...                     "name": "Aluminum",
            ...                     "node_type": "option",
            ...                     "price_impact_value": 50.00,
            ...                     "weight_impact": 2.0
            ...                 },
            ...                 {
            ...                     "name": "Vinyl",
            ...                     "node_type": "option",
            ...                     "price_impact_value": 30.00,
            ...                     "weight_impact": 1.5
            ...                 }
            ...             ]
            ...         }
            ...     ]
            ... }
            >>>
            >>> root = await service.create_hierarchy_from_dict(
            ...     manufacturing_type_id=1,
            ...     hierarchy_data=hierarchy
            ... )
            >>> # Creates: Frame Material → Material Type → [Aluminum, Vinyl]
        """
        from app.core.exceptions import (
            ConflictException,
            DatabaseException,
            NotFoundException,
            ValidationException,
        )

        # Validate hierarchy_data is a dictionary
        if not isinstance(hierarchy_data, dict):
            raise ValueError(
                f"hierarchy_data must be a dictionary, got {type(hierarchy_data).__name__}"
            )

        # Validate required fields
        if "name" not in hierarchy_data:
            raise ValueError("hierarchy_data must contain 'name' field")

        if "node_type" not in hierarchy_data:
            raise ValueError("hierarchy_data must contain 'node_type' field")

        # Make a copy to avoid modifying the original dict
        hierarchy_data = hierarchy_data.copy()

        # Extract children before creating node (we'll process them after)
        children_data = hierarchy_data.pop("children", [])

        # Validate children is a list if provided
        if children_data is not None and not isinstance(children_data, list):
            raise ValueError(f"'children' must be a list, got {type(children_data).__name__}")

        try:
            # Extract node data from dictionary
            node_data = {
                "manufacturing_type_id": manufacturing_type_id,
                "parent_node_id": parent.id if parent else None,
                **hierarchy_data,  # Spread all other fields from dict
            }

            # Convert Decimal fields if they're provided as strings or floats
            if "price_impact_value" in node_data and node_data["price_impact_value"] is not None:
                node_data["price_impact_value"] = Decimal(str(node_data["price_impact_value"]))

            if "weight_impact" in node_data and node_data["weight_impact"] is not None:
                node_data["weight_impact"] = Decimal(str(node_data["weight_impact"]))

            # Create the node - but don't commit yet if we're in a batch operation
            # We'll commit at the end of the root call
            from sqlalchemy import select

            from app.models.attribute_node import AttributeNode as AttributeNodeModel

            # Perform all the same validations as create_node
            name = node_data["name"]
            node_type = node_data["node_type"]

            # Validate manufacturing type exists
            mfg_type = await self.mfg_type_repo.get(manufacturing_type_id)
            if mfg_type is None:
                raise NotFoundException(
                    f"Manufacturing type with id {manufacturing_type_id} not found"
                )

            # Validate node_type
            valid_node_types = {"category", "attribute", "option", "component", "technical_spec"}
            if node_type not in valid_node_types:
                raise ValidationException(
                    f"Invalid node_type '{node_type}'. Must be one of: {', '.join(valid_node_types)}"
                )

            # Check for duplicate names at the same level
            siblings_query = select(AttributeNodeModel).where(
                AttributeNodeModel.manufacturing_type_id == manufacturing_type_id,
                AttributeNodeModel.parent_node_id == (parent.id if parent else None),
                AttributeNodeModel.name == name,
            )
            result = await self.attr_node_repo.db.execute(siblings_query)
            existing_sibling = result.scalar_one_or_none()

            if existing_sibling is not None:
                parent_desc = (
                    f"parent node {parent.id if parent else None}" if parent else "root level"
                )
                raise ConflictException(
                    f"A node with name '{name}' already exists at {parent_desc} "
                    f"in manufacturing type {manufacturing_type_id}"
                )

            # Calculate ltree_path and depth
            ltree_path = self._calculate_ltree_path(parent, name)
            depth = self._calculate_depth(parent)

            # Create the node model
            node = AttributeNodeModel(ltree_path=ltree_path, depth=depth, **node_data)

            # Add to session but don't commit yet
            self.attr_node_repo.db.add(node)
            await self.attr_node_repo.db.flush()  # Flush to get the ID

            # Recursively process children
            if children_data:
                for child_data in children_data:
                    # Validate each child is a dictionary
                    if not isinstance(child_data, dict):
                        raise ValueError(
                            f"Each child must be a dictionary, got {type(child_data).__name__} "
                            f"for child of node '{node.name}'"
                        )

                    # Recursively create child hierarchy (not a root call)
                    await self.create_hierarchy_from_dict(
                        manufacturing_type_id=manufacturing_type_id,
                        hierarchy_data=child_data,
                        parent=node,
                        _is_root_call=False,
                    )

            # Only commit if this is the root call
            if _is_root_call:
                await self.commit()
                await self.refresh(node)

            return node

        except Exception as e:
            # Only rollback if this is the root call
            if _is_root_call:
                await self.rollback()

            # Re-raise with additional context about which node failed
            node_name = hierarchy_data.get("name", "<unknown>")
            parent_name = parent.name if parent else "<root>"

            # For validation errors, preserve the original exception type
            if isinstance(
                e, (NotFoundException, ValidationException, ConflictException, ValueError)
            ):
                raise

            raise DatabaseException(
                f"Failed to create node '{node_name}' under parent '{parent_name}': {str(e)}"
            ) from e

    async def pydantify(
        self,
        manufacturing_type_id: int,
        root_node_id: int | None = None,
    ) -> list[AttributeNodeTree]:
        """Get hierarchy as Pydantic models (serializable to JSON).

        Retrieves the attribute tree for a manufacturing type and converts
        it to a nested Pydantic structure suitable for JSON serialization
        and tree visualization.

        Args:
            manufacturing_type_id: Manufacturing type ID
            root_node_id: Optional root node ID to get subtree only

        Returns:
            list[AttributeNodeTree]: List of root nodes with nested children

        Raises:
            NotFoundException: If manufacturing type or root node not found

        Example:
            >>> # Get full tree for manufacturing type
            >>> tree = await service.pydantify(manufacturing_type_id=1)
            >>>
            >>> # Get subtree starting from specific node
            >>> subtree = await service.pydantify(
            ...     manufacturing_type_id=1,
            ...     root_node_id=42
            ... )
            >>>
            >>> # Serialize to JSON
            >>> import json
            >>> tree_json = json.dumps([node.model_dump() for node in tree], indent=2)
        """
        from app.core.exceptions import NotFoundException
        from app.schemas.attribute_node import AttributeNodeTree

        # Validate manufacturing type exists
        mfg_type = await self.mfg_type_repo.get(manufacturing_type_id)
        if mfg_type is None:
            raise NotFoundException(f"Manufacturing type with id {manufacturing_type_id} not found")

        # If root_node_id is provided, validate it exists and build subtree
        if root_node_id is not None:
            root_node = await self.attr_node_repo.get(root_node_id)
            if root_node is None:
                raise NotFoundException(f"Root node with id {root_node_id} not found")

            # Validate root node belongs to the manufacturing type
            if root_node.manufacturing_type_id != manufacturing_type_id:
                raise ValueError(
                    f"Root node {root_node_id} belongs to manufacturing type "
                    f"{root_node.manufacturing_type_id}, not {manufacturing_type_id}"
                )

            # Get all descendants of the root node
            descendants = await self.attr_node_repo.get_descendants(root_node_id)
            # Include the root node itself at the beginning
            nodes = [root_node] + descendants

            # For subtree, we need to build the tree treating the specified node as root
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
            # The root of the subtree is the specified root_node_id
            for node in nodes:
                if node.id == root_node_id:
                    # This is the root of our subtree
                    continue

                node_tree = node_map[node.id]

                # Add to parent's children if parent is in our subtree
                if node.parent_node_id in node_map:
                    parent = node_map[node.parent_node_id]
                    parent.children.append(node_tree)

            # Return the root node as a single-item list
            return [node_map[root_node_id]]
        else:
            # Get all nodes for the manufacturing type
            nodes = await self.attr_node_repo.get_by_manufacturing_type(manufacturing_type_id)

            # Build tree structure using repository method
            tree = self.attr_node_repo.build_tree(nodes)

            return tree

    async def asciify(
        self,
        manufacturing_type_id: int,
        root_node_id: int | None = None,
    ) -> str:
        """Generate ASCII tree representation of the hierarchy.

        Creates a human-readable ASCII tree visualization using box-drawing
        characters (├──, └──, │) to show the hierarchical structure.
        Includes a virtual root node showing the manufacturing type name.

        Args:
            manufacturing_type_id: Manufacturing type ID
            root_node_id: Optional root node ID to visualize subtree only

        Returns:
            str: Formatted ASCII tree string

        Raises:
            NotFoundException: If manufacturing type or root node not found

        Example:
            >>> tree_str = await service.asciify(manufacturing_type_id=1)
            >>> print(tree_str)
            Material [category]
            ├── uPVC [category]
            │   ├── System [category]
            │   │   ├── Aluplast [option]
            │   │   │   └── Profile [attribute]
            │   │   │       └── IDEAL 4000 [option] [+$50.00]
            │   │   └── Kommerling [option]
            │   └── Size [category]
            └── Aluminium [category]
        """
        from app.core.exceptions import NotFoundException

        # Validate manufacturing type exists
        mfg_type = await self.mfg_type_repo.get(manufacturing_type_id)
        if mfg_type is None:
            raise NotFoundException(f"Manufacturing type with id {manufacturing_type_id} not found")

        # Get the tree structure using pydantify
        tree = await self.pydantify(manufacturing_type_id, root_node_id)

        if not tree:
            return "(Empty tree)"

        # Add virtual root node showing manufacturing type name
        lines = [mfg_type.name]  # Virtual root at the top

        # Build ASCII representation for each root node
        for i, root_node in enumerate(tree):
            is_last_root = i == len(tree) - 1
            lines.append(
                self._generate_ascii_tree_recursive(
                    node=root_node,
                    prefix="",
                    is_last=is_last_root,
                )
            )

        return "\n".join(lines)

    def _generate_ascii_tree_recursive(
        self,
        node: AttributeNodeTree,
        prefix: str = "",
        is_last: bool = True,
    ) -> str:
        """Recursively generate ASCII tree representation.

        Helper method that recursively builds the ASCII tree string using
        box-drawing characters to show hierarchy structure.

        Args:
            node: Current node to render
            prefix: Prefix string for indentation (accumulated from parents)
            is_last: Whether this is the last child of its parent

        Returns:
            str: Formatted ASCII tree string for this node and its descendants

        Example:
            >>> # Internal method, called by asciify()
            >>> result = service._generate_ascii_tree_recursive(
            ...     node=node,
            ...     prefix="",
            ...     is_last=True
            ... )
        """
        lines = []

        # Determine connector based on whether this is the last child
        connector = "└── " if is_last else "├── "

        # Format node name with type indicator
        node_display = f"{node.name} [{node.node_type}]"

        # Add price impact if present
        if node.price_impact_value is not None and node.price_impact_value != 0:
            # Format with 2 decimal places
            price_str = f"[+${node.price_impact_value:.2f}]"
            node_display += f" {price_str}"

        # Add depth indicator if helpful (for debugging)
        # Uncomment if you want to show depth: node_display += f" (depth: {node.depth})"

        # Build the current line
        current_line = f"{prefix}{connector}{node_display}"
        lines.append(current_line)

        # Process children
        if node.children:
            # Determine the prefix for children
            # If this is the last child, use spaces; otherwise use vertical bar
            child_prefix = prefix + ("    " if is_last else "│   ")

            for i, child in enumerate(node.children):
                is_last_child = i == len(node.children) - 1
                child_tree = self._generate_ascii_tree_recursive(
                    node=child,
                    prefix=child_prefix,
                    is_last=is_last_child,
                )
                lines.append(child_tree)

        return "\n".join(lines)

    async def plot_tree(
        self,
        manufacturing_type_id: int,
        root_node_id: int | None = None,
    ):
        """Generate graphical tree plot using Matplotlib.

        Creates a visual tree representation with nodes and edges, displaying
        node names, types, and price impacts. Uses NetworkX for automatic
        tree layout if available, otherwise falls back to manual positioning.

        Args:
            manufacturing_type_id: Manufacturing type ID
            root_node_id: Optional root node ID to visualize subtree only

        Returns:
            matplotlib.figure.Figure: Matplotlib figure object containing the tree plot

        Raises:
            NotFoundException: If manufacturing type or root node not found
            ImportError: If matplotlib is not installed

        Example:
            >>> # Generate tree plot
            >>> fig = await service.plot_tree(manufacturing_type_id=1)
            >>>
            >>> # Save to file
            >>> fig.savefig('hierarchy_tree.png', dpi=300, bbox_inches='tight')
            >>>
            >>> # Display in Jupyter notebook
            >>> import matplotlib.pyplot as plt
            >>> plt.show()
            >>>
            >>> # Get subtree plot
            >>> fig = await service.plot_tree(
            ...     manufacturing_type_id=1,
            ...     root_node_id=42
            ... )
        """
        try:
            import matplotlib.patches as mpatches
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError(
                "matplotlib is required for tree plotting. Install it with: pip install matplotlib"
            )

        from app.core.exceptions import NotFoundException

        # Validate manufacturing type exists
        mfg_type = await self.mfg_type_repo.get(manufacturing_type_id)
        if mfg_type is None:
            raise NotFoundException(f"Manufacturing type with id {manufacturing_type_id} not found")

        # Get all nodes for the manufacturing type
        if root_node_id is not None:
            root_node = await self.attr_node_repo.get(root_node_id)
            if root_node is None:
                raise NotFoundException(f"Root node with id {root_node_id} not found")

            # Validate root node belongs to the manufacturing type
            if root_node.manufacturing_type_id != manufacturing_type_id:
                raise ValueError(
                    f"Root node {root_node_id} belongs to manufacturing type "
                    f"{root_node.manufacturing_type_id}, not {manufacturing_type_id}"
                )

            # Get all descendants of the root node
            descendants = await self.attr_node_repo.get_descendants(root_node_id)
            nodes = [root_node] + descendants
        else:
            nodes = await self.attr_node_repo.get_by_manufacturing_type(manufacturing_type_id)

        if not nodes:
            # Create empty figure with message
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No nodes found", ha="center", va="center", fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            return fig

        # Build parent → children map
        children_map: dict[int | None, list[AttributeNode]] = {}
        for node in nodes:
            parent_id = node.parent_node_id
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(node)

        # Sort children by sort_order
        for children in children_map.values():
            children.sort(key=lambda n: n.sort_order)

        # Try to use NetworkX for better layout
        try:
            import networkx as nx

            use_networkx = True
        except ImportError:
            use_networkx = False

        if use_networkx:
            # Use NetworkX for automatic tree layout
            fig = self._plot_tree_with_networkx(nodes, children_map, mfg_type.name)
        else:
            # Fall back to manual recursive layout
            fig = self._plot_tree_manual(nodes, children_map, mfg_type.name)

        return fig

    @staticmethod
    def _plot_tree_with_networkx(
        nodes: list[AttributeNode],
        children_map: dict[int | None, list[AttributeNode]],
        title: str,
    ):
        """Plot tree using NetworkX with proper hierarchical tree layout.

        Creates a proper tree diagram with root at top and children arranged
        in levels below, ensuring a tidy hierarchical structure.

        Args:
            nodes: List of all nodes to plot
            children_map: Mapping of parent_id to list of children
            title: Title for the plot (manufacturing type name)

        Returns:
            matplotlib.figure.Figure: Matplotlib figure object
        """
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        import networkx as nx

        # Create directed graph
        G = nx.DiGraph()

        # Add nodes with attributes
        node_labels = {}
        node_colors_map = {}
        node_type_colors = {
            "category": "#FFE5B4",  # Peach
            "attribute": "#B4D7FF",  # Light blue
            "option": "#B4FFB4",  # Light green
            "component": "#FFB4E5",  # Light pink
            "technical_spec": "#E5B4FF",  # Light purple
        }

        # Create a set of node IDs for quick lookup
        node_ids = {node.id for node in nodes}
        node_map = {node.id: node for node in nodes}

        for node in nodes:
            G.add_node(node.id)

            # Format node label with name, type, and price
            label = f"{node.name}\n({node.node_type})"
            if node.price_impact_value is not None and node.price_impact_value != 0:
                label += f"\n[+${node.price_impact_value:.2f}]"

            node_labels[node.id] = label
            node_colors_map[node.id] = node_type_colors.get(node.node_type, "#CCCCCC")

        # Add edges (parent → child relationships)
        for node in nodes:
            if node.parent_node_id is not None and node.parent_node_id in node_ids:
                G.add_edge(node.parent_node_id, node.id)

        # Find root nodes (nodes with no parent or parent not in graph)
        root_nodes = [n.id for n in nodes if n.parent_node_id is None or n.parent_node_id not in G]

        # Add VIRTUAL ROOT NODE for visualization (Option A implementation)
        # This shows the manufacturing type name at the top without changing database
        # NOTE: For true database root, see option_b_future_implementation.md
        virtual_root_id = -1  # Use negative ID to avoid conflicts
        G.add_node(virtual_root_id)
        node_labels[virtual_root_id] = f"{title}\\n(Manufacturing Type)"
        node_colors_map[virtual_root_id] = "#FFD700"  # Gold color for root

        # Connect all actual roots to virtual root
        for root_id in root_nodes:
            G.add_edge(virtual_root_id, root_id)

        # Create PROPER hierarchical layout using custom algorithm
        # This ensures root is at top and children are arranged level by level
        pos = {}

        # Define spacing first
        y_spacing = 2.0  # Vertical spacing between levels

        # Position virtual root at the very top
        pos[virtual_root_id] = (0, 1 * y_spacing)  # Above all other nodes

        # Group nodes by depth level
        levels = {}
        for node in nodes:
            depth = node.depth
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(node.id)

        # Calculate positions level by level
        max_depth = max(levels.keys()) if levels else 0

        for depth in sorted(levels.keys()):
            level_nodes = levels[depth]
            num_nodes = len(level_nodes)

            # Calculate horizontal spacing to spread nodes evenly
            if num_nodes == 1:
                x_positions = [0]
            else:
                # Spread nodes across width based on number of nodes
                total_width = max(10, num_nodes * 2)
                x_positions = [
                    i * (total_width / (num_nodes - 1)) - total_width / 2 for i in range(num_nodes)
                ]

            # Assign positions (y increases downward, so negate depth)
            y = -depth * y_spacing
            for i, node_id in enumerate(level_nodes):
                pos[node_id] = (x_positions[i], y)

        # Adjust positions to center children under parents
        for depth in sorted(levels.keys(), reverse=True)[1:]:  # Skip deepest level
            for node_id in levels[depth]:
                # Get children of this node
                children = children_map.get(node_id, [])
                if children:
                    # Calculate average x position of children
                    child_x_positions = [pos[child.id][0] for child in children if child.id in pos]
                    if child_x_positions:
                        avg_x = sum(child_x_positions) / len(child_x_positions)
                        # Update parent position to be centered above children
                        pos[node_id] = (avg_x, pos[node_id][1])

        # Create figure with more space for title
        fig, ax = plt.subplots(figsize=(20, 14))

        # Draw edges
        nx.draw_networkx_edges(
            G,
            pos,
            ax=ax,
            edge_color="#666666",
            arrows=False,  # Remove arrows for cleaner look
            width=2,
            alpha=0.5,
        )

        # Draw nodes - get colors in the same order as nodes in G
        node_colors = [node_colors_map[node_id] for node_id in G.nodes()]
        nx.draw_networkx_nodes(
            G,
            pos,
            ax=ax,
            node_color=node_colors,
            node_size=4000,
            node_shape="o",
            alpha=0.9,
            edgecolors="#333333",
            linewidths=2.5,
        )

        # Draw labels
        nx.draw_networkx_labels(
            G,
            pos,
            ax=ax,
            labels=node_labels,
            font_size=9,
            font_weight="bold",
            font_family="sans-serif",
        )

        # Add title with extra padding to prevent cutoff
        ax.set_title(f"Attribute Hierarchy: {title}", fontsize=18, fontweight="bold", pad=30)

        # Add legend
        legend_elements = [
            mpatches.Patch(facecolor=color, edgecolor="#333333", label=node_type.capitalize())
            for node_type, color in node_type_colors.items()
        ]
        ax.legend(handles=legend_elements, loc="upper left", fontsize=11, framealpha=0.9)

        ax.axis("off")

        # Use tight_layout with extra padding to prevent title cutoff
        plt.tight_layout(pad=2.0)

        return fig

    def _plot_tree_manual(
        self,
        nodes: list[AttributeNode],
        children_map: dict[int | None, list[AttributeNode]],
        title: str,
    ):
        """Plot tree using manual hierarchical layout.

        Fallback method when NetworkX is not available. Uses a proper
        hierarchical algorithm to position nodes level-by-level from top to bottom.

        Args:
            nodes: List of all nodes to plot
            children_map: Mapping of parent_id to list of children
            title: Title for the plot (manufacturing type name)

        Returns:
            matplotlib.figure.Figure: Matplotlib figure object
        """
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt

        # Node type colors
        node_type_colors = {
            "category": "#FFE5B4",  # Peach
            "attribute": "#B4D7FF",  # Light blue
            "option": "#B4FFB4",  # Light green
            "component": "#FFB4E5",  # Light pink
            "technical_spec": "#E5B4FF",  # Light purple
        }

        # Calculate positions using hierarchical layout
        positions = {}
        node_info = {node.id: node for node in nodes}

        # Find root nodes
        root_nodes = children_map.get(None, [])

        if not root_nodes:
            # No root nodes found, create empty figure
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No root nodes found", ha="center", va="center", fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            return fig

        # Group nodes by depth level
        levels = {}
        for node in nodes:
            depth = node.depth
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(node.id)

        # Calculate positions level by level
        max_depth = max(levels.keys()) if levels else 0
        y_spacing = 2.0  # Vertical spacing between levels

        for depth in sorted(levels.keys()):
            level_nodes = levels[depth]
            num_nodes = len(level_nodes)

            # Calculate horizontal spacing to spread nodes evenly
            if num_nodes == 1:
                x_positions = [0]
            else:
                # Spread nodes across width based on number of nodes
                total_width = max(10, num_nodes * 2)
                x_positions = [
                    i * (total_width / (num_nodes - 1)) - total_width / 2 for i in range(num_nodes)
                ]

            # Assign positions (y increases downward, so negate depth)
            y = -depth * y_spacing
            for i, node_id in enumerate(level_nodes):
                positions[node_id] = (x_positions[i], y)

        # Adjust positions to center children under parents
        for depth in sorted(levels.keys(), reverse=True)[1:]:  # Skip deepest level
            for node_id in levels[depth]:
                # Get children of this node
                children = children_map.get(node_id, [])
                if children:
                    # Calculate average x position of children
                    child_x_positions = [
                        positions[child.id][0] for child in children if child.id in positions
                    ]
                    if child_x_positions:
                        avg_x = sum(child_x_positions) / len(child_x_positions)
                        # Update parent position to be centered above children
                        positions[node_id] = (avg_x, positions[node_id][1])

        # Create figure with more space for title
        fig, ax = plt.subplots(figsize=(20, 14))

        # Draw edges
        for node in nodes:
            if node.parent_node_id is not None and node.parent_node_id in positions:
                parent_pos = positions[node.parent_node_id]
                child_pos = positions[node.id]
                ax.plot(
                    [parent_pos[0], child_pos[0]],
                    [parent_pos[1], child_pos[1]],
                    "k-",
                    linewidth=2,
                    alpha=0.5,
                    zorder=1,
                )

        # Draw nodes
        for node in nodes:
            if node.id in positions:
                x, y = positions[node.id]
                color = node_type_colors.get(node.node_type, "#CCCCCC")

                # Draw node circle
                circle = plt.Circle(
                    (x, y),
                    0.4,
                    facecolor=color,
                    edgecolor="#333333",
                    linewidth=2.5,
                    alpha=0.9,
                    zorder=2,
                )
                ax.add_patch(circle)

                # Format label
                label = f"{node.name}\n({node.node_type})"
                if node.price_impact_value is not None and node.price_impact_value != 0:
                    label += f"\n[+${node.price_impact_value:.2f}]"

                # Draw label
                ax.text(
                    x, y, label, ha="center", va="center", fontsize=9, fontweight="bold", zorder=3
                )

        # Add title with extra padding to prevent cutoff
        ax.set_title(f"Attribute Hierarchy: {title}", fontsize=18, fontweight="bold", pad=30)

        # Add legend
        legend_elements = [
            mpatches.Patch(facecolor=color, edgecolor="#333333", label=node_type.capitalize())
            for node_type, color in node_type_colors.items()
        ]
        ax.legend(handles=legend_elements, loc="upper left", fontsize=11, framealpha=0.9)

        # Set axis properties
        ax.set_aspect("equal")
        ax.axis("off")

        # Auto-scale with padding
        if positions:
            x_coords = [pos[0] for pos in positions.values()]
            y_coords = [pos[1] for pos in positions.values()]
            x_margin = (max(x_coords) - min(x_coords)) * 0.1 + 1
            y_margin = (max(y_coords) - min(y_coords)) * 0.1 + 1
            ax.set_xlim(min(x_coords) - x_margin, max(x_coords) + x_margin)
            ax.set_ylim(min(y_coords) - y_margin, max(y_coords) + y_margin)

        # Use tight_layout with extra padding to prevent title cutoff
        plt.tight_layout(pad=2.0)

        return fig
