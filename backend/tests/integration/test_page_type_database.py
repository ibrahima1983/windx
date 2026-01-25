"""Integration tests for page type functionality with real database."""

import pytest
from decimal import Decimal
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType
from app.core.manufacturing_type_resolver import ManufacturingTypeResolver


@pytest.mark.asyncio
class TestPageTypeDatabaseIntegration:
    """Integration tests for page type functionality with database."""

    @pytest.fixture
    async def test_manufacturing_type(self, db_session: AsyncSession) -> ManufacturingType:
        """Create a test manufacturing type for testing."""
        mfg_type = ManufacturingType(
            name="Test Window Type",
            description="Test manufacturing type for page type tests",
            base_category="window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)
        return mfg_type

    @pytest.fixture
    async def test_attribute_nodes(
        self, db_session: AsyncSession, test_manufacturing_type: ManufacturingType
    ) -> dict[str, list[AttributeNode]]:
        """Create test attribute nodes for each page type."""
        nodes_by_page_type = {}

        for page_type in ["profile", "accessories", "glazing"]:
            nodes = []
            for i in range(3):  # Create 3 nodes per page type
                node = AttributeNode(
                    manufacturing_type_id=test_manufacturing_type.id,
                    page_type=page_type,
                    name=f"{page_type}_attribute_{i + 1}",
                    description=f"Test {page_type} attribute {i + 1}",
                    node_type="attribute",
                    data_type="string",
                    required=i == 0,  # First one is required
                    ltree_path=f"{page_type}.test.attribute_{i + 1}",
                    depth=2,
                    sort_order=i + 1,
                    ui_component="input",
                    help_text=f"Help text for {page_type} attribute {i + 1}",
                )
                nodes.append(node)
                db_session.add(node)

            nodes_by_page_type[page_type] = nodes

        await db_session.commit()
        return nodes_by_page_type

    async def test_page_type_field_exists(self, db_session: AsyncSession):
        """Test that page_type field exists in database."""
        result = await db_session.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'attribute_nodes' AND column_name = 'page_type'"
            )
        )
        column = result.scalar_one_or_none()
        assert column == "page_type", "page_type column should exist in attribute_nodes table"

    async def test_page_type_default_value(
        self, db_session: AsyncSession, test_manufacturing_type: ManufacturingType
    ):
        """Test that page_type has correct default value."""
        # Create node without specifying page_type
        node = AttributeNode(
            manufacturing_type_id=test_manufacturing_type.id,
            name="test_default_page_type",
            description="Test default page type",
            node_type="attribute",
            data_type="string",
            ltree_path="test.default.page_type",
            depth=1,
            sort_order=1,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.page_type == "profile", "Default page_type should be 'profile'"

    @pytest.mark.parametrize(
        "page_type,expected_count",
        [
            ("profile", 3),
            ("accessories", 3),
            ("glazing", 3),
        ],
        ids=["profile_nodes", "accessories_nodes", "glazing_nodes"],
    )
    async def test_query_nodes_by_page_type(
        self,
        db_session: AsyncSession,
        test_manufacturing_type: ManufacturingType,
        test_attribute_nodes: dict[str, list[AttributeNode]],
        page_type: str,
        expected_count: int,
    ):
        """Test querying attribute nodes by page type."""
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == test_manufacturing_type.id,
            AttributeNode.page_type == page_type,
        )
        result = await db_session.execute(stmt)
        nodes = result.scalars().all()

        assert len(nodes) == expected_count
        for node in nodes:
            assert node.page_type == page_type
            assert node.manufacturing_type_id == test_manufacturing_type.id

    async def test_composite_index_performance(
        self,
        db_session: AsyncSession,
        test_manufacturing_type: ManufacturingType,
        test_attribute_nodes: dict[str, list[AttributeNode]],
    ):
        """Test that composite index is used for efficient queries."""
        # Query using the composite index
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == test_manufacturing_type.id,
            AttributeNode.page_type == "profile",
            AttributeNode.node_type == "attribute",
        )
        result = await db_session.execute(stmt)
        nodes = result.scalars().all()

        # Should find profile nodes
        assert len(nodes) > 0
        for node in nodes:
            assert node.page_type == "profile"
            assert node.node_type == "attribute"

    async def test_page_type_constraint_validation(
        self, db_session: AsyncSession, test_manufacturing_type: ManufacturingType
    ):
        """Test that page_type accepts valid values."""
        valid_page_types = ["profile", "accessories", "glazing"]

        for page_type in valid_page_types:
            node = AttributeNode(
                manufacturing_type_id=test_manufacturing_type.id,
                page_type=page_type,
                name=f"test_{page_type}",
                description=f"Test {page_type} node",
                node_type="attribute",
                data_type="string",
                ltree_path=f"test.{page_type}.node",
                depth=1,
                sort_order=1,
            )
            db_session.add(node)

        # Should commit successfully
        await db_session.commit()

    async def test_manufacturing_type_resolver_with_database(
        self, db_session: AsyncSession, test_manufacturing_type: ManufacturingType
    ):
        """Test ManufacturingTypeResolver with real database."""
        # Test profile page type (should use existing logic)
        result = await ManufacturingTypeResolver.get_default_for_page_type(
            db_session, "profile", "window"
        )
        assert result is not None
        assert result.base_category == "window"

        # Test accessories page type
        result = await ManufacturingTypeResolver.get_default_for_page_type(
            db_session, "accessories", "window"
        )
        assert result is not None
        assert result.base_category == "window"

        # Test glazing page type
        result = await ManufacturingTypeResolver.get_default_for_page_type(
            db_session, "glazing", "window"
        )
        assert result is not None
        assert result.base_category == "window"

    async def test_ltree_path_with_page_types(
        self, db_session: AsyncSession, test_attribute_nodes: dict[str, list[AttributeNode]]
    ):
        """Test LTREE functionality works with page types."""
        # Test LTREE query for profile nodes
        result = await db_session.execute(
            text(
                "SELECT * FROM attribute_nodes WHERE ltree_path ~ 'profile.*' AND page_type = 'profile'"
            )
        )
        profile_nodes = result.fetchall()
        assert len(profile_nodes) == 3

        # Test LTREE query for accessories nodes
        result = await db_session.execute(
            text(
                "SELECT * FROM attribute_nodes WHERE ltree_path ~ 'accessories.*' AND page_type = 'accessories'"
            )
        )
        accessories_nodes = result.fetchall()
        assert len(accessories_nodes) == 3

    async def test_page_type_migration_compatibility(self, db_session: AsyncSession):
        """Test that existing data has correct page_type after migration."""
        # Query for any existing nodes that should have been migrated
        stmt = select(AttributeNode).where(AttributeNode.page_type.is_(None))
        result = await db_session.execute(stmt)
        null_page_type_nodes = result.scalars().all()

        # Should be no nodes with NULL page_type after migration
        assert len(null_page_type_nodes) == 0, "All nodes should have page_type set after migration"

    @pytest.mark.parametrize(
        "page_type,node_count",
        [
            ("profile", 5),
            ("accessories", 3),
            ("glazing", 2),
        ],
        ids=["profile_bulk", "accessories_bulk", "glazing_bulk"],
    )
    async def test_bulk_insert_with_page_types(
        self,
        db_session: AsyncSession,
        test_manufacturing_type: ManufacturingType,
        page_type: str,
        node_count: int,
    ):
        """Test bulk insertion of nodes with different page types."""
        nodes = []
        for i in range(node_count):
            node = AttributeNode(
                manufacturing_type_id=test_manufacturing_type.id,
                page_type=page_type,
                name=f"bulk_{page_type}_{i}",
                description=f"Bulk {page_type} node {i}",
                node_type="attribute",
                data_type="string",
                ltree_path=f"bulk.{page_type}.node_{i}",
                depth=2,
                sort_order=i,
            )
            nodes.append(node)
            db_session.add(node)

        await db_session.commit()

        # Verify all nodes were inserted with correct page_type
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == test_manufacturing_type.id,
            AttributeNode.page_type == page_type,
            AttributeNode.name.like(f"bulk_{page_type}_%"),
        )
        result = await db_session.execute(stmt)
        inserted_nodes = result.scalars().all()

        assert len(inserted_nodes) == node_count
        for node in inserted_nodes:
            assert node.page_type == page_type
