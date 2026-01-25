"""Integration tests for batch hierarchy creation from dictionaries.

Tests the create_hierarchy_from_dict method with various scenarios including:
- Simple hierarchies
- Nested hierarchies with multiple levels
- Transaction rollback on errors
- Error handling and validation
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType
from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.fixture
async def hierarchy_service(db_session: AsyncSession) -> HierarchyBuilderService:
    """Create HierarchyBuilderService instance."""
    return HierarchyBuilderService(db_session)


@pytest.fixture
async def sample_mfg_type(
    hierarchy_service: HierarchyBuilderService,
) -> ManufacturingType:
    """Create a sample manufacturing type for testing."""
    return await hierarchy_service.create_manufacturing_type(
        name="Test Window",
        description="Test window for batch creation",
        base_category="window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
    )


class TestCreateHierarchyFromDict:
    """Test suite for create_hierarchy_from_dict method."""

    async def test_create_simple_hierarchy_no_children(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test creating a single node without children."""
        hierarchy_data = {
            "name": "Frame Material",
            "node_type": "category",
            "description": "Frame material options",
        }

        root = await hierarchy_service.create_hierarchy_from_dict(
            manufacturing_type_id=sample_mfg_type.id,
            hierarchy_data=hierarchy_data,
        )

        assert root is not None
        assert root.name == "Frame Material"
        assert root.node_type == "category"
        assert root.description == "Frame material options"
        assert root.ltree_path == "frame_material"
        assert root.depth == 0
        assert root.parent_node_id is None

    async def test_create_hierarchy_with_one_level_children(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test creating a hierarchy with one level of children."""
        hierarchy_data = {
            "name": "Frame Material",
            "node_type": "category",
            "children": [
                {
                    "name": "Aluminum",
                    "node_type": "option",
                    "price_impact_value": 50.00,
                    "weight_impact": 2.0,
                },
                {
                    "name": "Vinyl",
                    "node_type": "option",
                    "price_impact_value": 30.00,
                    "weight_impact": 1.5,
                },
            ],
        }

        root = await hierarchy_service.create_hierarchy_from_dict(
            manufacturing_type_id=sample_mfg_type.id,
            hierarchy_data=hierarchy_data,
        )

        # Verify root node
        assert root.name == "Frame Material"
        assert root.depth == 0

        # Verify children were created
        children = await hierarchy_service.attr_node_repo.get_children(root.id)
        assert len(children) == 2

        # Verify first child
        aluminum = next(c for c in children if c.name == "Aluminum")
        assert aluminum.node_type == "option"
        assert aluminum.price_impact_value == Decimal("50.00")
        assert aluminum.weight_impact == Decimal("2.0")
        assert aluminum.ltree_path == "frame_material.aluminum"
        assert aluminum.depth == 1
        assert aluminum.parent_node_id == root.id

        # Verify second child
        vinyl = next(c for c in children if c.name == "Vinyl")
        assert vinyl.node_type == "option"
        assert vinyl.price_impact_value == Decimal("30.00")
        assert vinyl.weight_impact == Decimal("1.5")
        assert vinyl.ltree_path == "frame_material.vinyl"
        assert vinyl.depth == 1
        assert vinyl.parent_node_id == root.id

    async def test_create_deeply_nested_hierarchy(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test creating a hierarchy with multiple nested levels."""
        hierarchy_data = {
            "name": "Frame Options",
            "node_type": "category",
            "children": [
                {
                    "name": "Material Type",
                    "node_type": "attribute",
                    "data_type": "selection",
                    "children": [
                        {
                            "name": "Aluminum",
                            "node_type": "option",
                            "price_impact_value": 50.00,
                            "children": [
                                {
                                    "name": "Finish",
                                    "node_type": "attribute",
                                    "data_type": "selection",
                                    "children": [
                                        {
                                            "name": "Brushed",
                                            "node_type": "option",
                                            "price_impact_value": 10.00,
                                        },
                                        {
                                            "name": "Polished",
                                            "node_type": "option",
                                            "price_impact_value": 15.00,
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "name": "Vinyl",
                            "node_type": "option",
                            "price_impact_value": 30.00,
                        },
                    ],
                }
            ],
        }

        root = await hierarchy_service.create_hierarchy_from_dict(
            manufacturing_type_id=sample_mfg_type.id,
            hierarchy_data=hierarchy_data,
        )

        # Verify root
        assert root.name == "Frame Options"
        assert root.depth == 0
        assert root.ltree_path == "frame_options"

        # Verify level 1 (Material Type)
        level1 = await hierarchy_service.attr_node_repo.get_children(root.id)
        assert len(level1) == 1
        material_type = level1[0]
        assert material_type.name == "Material Type"
        assert material_type.depth == 1
        assert material_type.ltree_path == "frame_options.material_type"

        # Verify level 2 (Aluminum, Vinyl)
        level2 = await hierarchy_service.attr_node_repo.get_children(material_type.id)
        assert len(level2) == 2
        aluminum = next(c for c in level2 if c.name == "Aluminum")
        vinyl = next(c for c in level2 if c.name == "Vinyl")
        assert aluminum.depth == 2
        assert aluminum.ltree_path == "frame_options.material_type.aluminum"
        assert vinyl.depth == 2
        assert vinyl.ltree_path == "frame_options.material_type.vinyl"

        # Verify level 3 (Finish under Aluminum)
        level3 = await hierarchy_service.attr_node_repo.get_children(aluminum.id)
        assert len(level3) == 1
        finish = level3[0]
        assert finish.name == "Finish"
        assert finish.depth == 3
        assert finish.ltree_path == "frame_options.material_type.aluminum.finish"

        # Verify level 4 (Brushed, Polished)
        level4 = await hierarchy_service.attr_node_repo.get_children(finish.id)
        assert len(level4) == 2
        brushed = next(c for c in level4 if c.name == "Brushed")
        polished = next(c for c in level4 if c.name == "Polished")
        assert brushed.depth == 4
        assert brushed.ltree_path == "frame_options.material_type.aluminum.finish.brushed"
        assert polished.depth == 4
        assert polished.ltree_path == "frame_options.material_type.aluminum.finish.polished"

    async def test_create_hierarchy_with_parent_node(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test creating a hierarchy under an existing parent node."""
        # First create a parent node
        parent = await hierarchy_service.create_node(
            manufacturing_type_id=sample_mfg_type.id,
            name="Existing Parent",
            node_type="category",
        )

        # Now create hierarchy under this parent
        hierarchy_data = {
            "name": "Child Category",
            "node_type": "category",
            "children": [
                {
                    "name": "Option 1",
                    "node_type": "option",
                },
                {
                    "name": "Option 2",
                    "node_type": "option",
                },
            ],
        }

        root = await hierarchy_service.create_hierarchy_from_dict(
            manufacturing_type_id=sample_mfg_type.id,
            hierarchy_data=hierarchy_data,
            parent=parent,
        )

        # Verify root is child of parent
        assert root.parent_node_id == parent.id
        assert root.depth == 1
        assert root.ltree_path == "existing_parent.child_category"

        # Verify children
        children = await hierarchy_service.attr_node_repo.get_children(root.id)
        assert len(children) == 2
        assert all(c.depth == 2 for c in children)
        assert all(c.ltree_path.startswith("existing_parent.child_category.") for c in children)

    async def test_create_hierarchy_with_all_node_fields(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test creating a hierarchy with all possible node fields."""
        hierarchy_data = {
            "name": "Complete Node",
            "node_type": "attribute",
            "data_type": "number",
            "display_condition": {"field": "parent", "operator": "equals", "value": "test"},
            "validation_rules": {"min": 0, "max": 100},
            "required": True,
            "price_impact_type": "percentage",
            "price_impact_value": 15.00,
            "price_formula": "base_price * 1.15",
            "weight_impact": 5.5,
            "weight_formula": "base_weight * 1.1",
            "technical_property_type": "u_value",
            "technical_impact_formula": "1 / r_value",
            "sort_order": 10,
            "ui_component": "slider",
            "description": "Test description",
            "help_text": "Test help text",
        }

        root = await hierarchy_service.create_hierarchy_from_dict(
            manufacturing_type_id=sample_mfg_type.id,
            hierarchy_data=hierarchy_data,
        )

        # Verify all fields were set correctly
        assert root.name == "Complete Node"
        assert root.node_type == "attribute"
        assert root.data_type == "number"
        assert root.display_condition == {"field": "parent", "operator": "equals", "value": "test"}
        assert root.validation_rules == {"min": 0, "max": 100}
        assert root.required is True
        assert root.price_impact_type == "percentage"
        assert root.price_impact_value == Decimal("15.00")
        assert root.price_formula == "base_price * 1.15"
        assert root.weight_impact == Decimal("5.5")
        assert root.weight_formula == "base_weight * 1.1"
        assert root.technical_property_type == "u_value"
        assert root.technical_impact_formula == "1 / r_value"
        assert root.sort_order == 10
        assert root.ui_component == "slider"
        assert root.description == "Test description"
        assert root.help_text == "Test help text"


class TestCreateHierarchyFromDictValidation:
    """Test validation and error handling for create_hierarchy_from_dict."""

    async def test_invalid_hierarchy_data_not_dict(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that non-dict hierarchy_data raises ValueError."""
        with pytest.raises(ValueError, match="hierarchy_data must be a dictionary"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data="not a dict",  # type: ignore
            )

    async def test_missing_name_field(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that missing 'name' field raises ValueError."""
        hierarchy_data = {
            "node_type": "category",
        }

        with pytest.raises(ValueError, match="hierarchy_data must contain 'name' field"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

    async def test_missing_node_type_field(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that missing 'node_type' field raises ValueError."""
        hierarchy_data = {
            "name": "Test Node",
        }

        with pytest.raises(ValueError, match="hierarchy_data must contain 'node_type' field"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

    async def test_invalid_children_not_list(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that non-list children raises ValueError."""
        hierarchy_data = {
            "name": "Test Node",
            "node_type": "category",
            "children": "not a list",  # Invalid
        }

        with pytest.raises(ValueError, match="'children' must be a list"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

    async def test_invalid_child_not_dict(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that non-dict child raises ValueError."""
        hierarchy_data = {
            "name": "Test Node",
            "node_type": "category",
            "children": [
                "not a dict",  # Invalid child
            ],
        }

        with pytest.raises(ValueError, match="Each child must be a dictionary"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

    async def test_invalid_manufacturing_type_id(
        self,
        hierarchy_service: HierarchyBuilderService,
    ):
        """Test that invalid manufacturing_type_id raises NotFoundException."""
        hierarchy_data = {
            "name": "Test Node",
            "node_type": "category",
        }

        with pytest.raises(NotFoundException, match="Manufacturing type with id 99999 not found"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=99999,
                hierarchy_data=hierarchy_data,
            )

    async def test_invalid_node_type(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that invalid node_type raises ValidationException."""
        hierarchy_data = {
            "name": "Test Node",
            "node_type": "invalid_type",
        }

        with pytest.raises(ValidationException, match="Invalid node_type"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

    async def test_duplicate_name_at_same_level(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that duplicate names at same level raise ConflictException."""
        # First create a node
        await hierarchy_service.create_node(
            manufacturing_type_id=sample_mfg_type.id,
            name="Existing Node",
            node_type="category",
        )

        # Try to create hierarchy with same name at root level
        hierarchy_data = {
            "name": "Existing Node",
            "node_type": "category",
        }

        with pytest.raises(ConflictException, match="already exists"):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )


class TestCreateHierarchyFromDictTransactions:
    """Test transaction handling and rollback for create_hierarchy_from_dict."""

    async def test_rollback_on_error_in_child_creation(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test that entire hierarchy is rolled back if child creation fails."""
        hierarchy_data = {
            "name": "Parent Node",
            "node_type": "category",
            "children": [
                {
                    "name": "Valid Child",
                    "node_type": "option",
                },
                {
                    "name": "Invalid Child",
                    "node_type": "invalid_type",  # This will cause error
                },
            ],
        }

        # Count nodes before
        from sqlalchemy import func, select

        count_before = await db_session.scalar(select(func.count()).select_from(AttributeNode))

        # Try to create hierarchy (should fail with ValidationException)
        with pytest.raises(ValidationException):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

        # Verify no nodes were created (rollback successful)
        count_after = await db_session.scalar(select(func.count()).select_from(AttributeNode))
        assert count_after == count_before

    async def test_rollback_on_error_in_nested_child(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test that entire hierarchy is rolled back if deeply nested child fails."""
        hierarchy_data = {
            "name": "Level 1",
            "node_type": "category",
            "children": [
                {
                    "name": "Level 2",
                    "node_type": "category",
                    "children": [
                        {
                            "name": "Level 3",
                            "node_type": "category",
                            "children": [
                                {
                                    "name": "Level 4 - Invalid",
                                    "node_type": "invalid_type",  # Error at level 4
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        # Count nodes before
        from sqlalchemy import func, select

        count_before = await db_session.scalar(select(func.count()).select_from(AttributeNode))

        # Try to create hierarchy (should fail with ValidationException)
        with pytest.raises(ValidationException):
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

        # Verify no nodes were created (rollback successful)
        count_after = await db_session.scalar(select(func.count()).select_from(AttributeNode))
        assert count_after == count_before

    async def test_error_message_includes_context(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
    ):
        """Test that error message includes context about which node failed."""
        hierarchy_data = {
            "name": "Parent Node",
            "node_type": "category",
            "children": [
                {
                    "name": "Failing Child",
                    "node_type": "invalid_type",
                }
            ],
        }

        # ValidationException is raised directly (not wrapped in DatabaseException)
        with pytest.raises(ValidationException) as exc_info:
            await hierarchy_service.create_hierarchy_from_dict(
                manufacturing_type_id=sample_mfg_type.id,
                hierarchy_data=hierarchy_data,
            )

        error_message = str(exc_info.value)
        # The error message should mention the invalid node_type
        assert "invalid_type" in error_message
        assert "node_type" in error_message

    async def test_successful_creation_commits_all_nodes(
        self,
        hierarchy_service: HierarchyBuilderService,
        sample_mfg_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test that successful creation commits all nodes."""
        hierarchy_data = {
            "name": "Root",
            "node_type": "category",
            "children": [
                {
                    "name": "Child 1",
                    "node_type": "option",
                },
                {
                    "name": "Child 2",
                    "node_type": "option",
                    "children": [
                        {
                            "name": "Grandchild",
                            "node_type": "option",
                        }
                    ],
                },
            ],
        }

        # Count nodes before
        from sqlalchemy import func, select

        count_before = await db_session.scalar(select(func.count()).select_from(AttributeNode))

        # Create hierarchy
        root = await hierarchy_service.create_hierarchy_from_dict(
            manufacturing_type_id=sample_mfg_type.id,
            hierarchy_data=hierarchy_data,
        )

        # Verify all nodes were created (4 total: root + 2 children + 1 grandchild)
        count_after = await db_session.scalar(select(func.count()).select_from(AttributeNode))
        assert count_after == count_before + 4

        # Verify we can query the created nodes
        descendants = await hierarchy_service.attr_node_repo.get_descendants(root.id)
        assert len(descendants) == 3  # 2 children + 1 grandchild
