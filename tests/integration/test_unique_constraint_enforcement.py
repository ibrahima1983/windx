"""Integration tests for unique constraint enforcement on attribute nodes.

This module tests that the unique constraint on (manufacturing_type_id, page_type, name)
properly prevents duplicate attribute names within the same manufacturing type and page type.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType


class TestUniqueConstraintEnforcement:
    """Test suite for unique constraint enforcement on attribute nodes."""

    @pytest.mark.asyncio
    async def test_unique_constraint_prevents_duplicate_names(self, db_session: AsyncSession):
        """Test that unique constraint prevents duplicate attribute names in same manufacturing type and page type."""
        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name="Test Unique Manufacturing Type",
            description="Test manufacturing type for unique constraint testing",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Create first attribute
        first_attribute = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            name="unique_test_attribute",
            node_type="attribute",
            data_type="string",
            page_type="profile",
            ltree_path="test.unique_attribute",
            depth=1,
            sort_order=1,
        )
        db_session.add(first_attribute)
        await db_session.commit()

        # Verify first attribute was created
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == "profile",
            AttributeNode.name == "unique_test_attribute",
        )
        result = await db_session.execute(stmt)
        created_attr = result.scalar_one_or_none()
        assert created_attr is not None

        # Try to create duplicate - this should fail with IntegrityError
        with pytest.raises(IntegrityError) as exc_info:
            duplicate_attribute = AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="unique_test_attribute",  # Same name
                node_type="attribute",
                data_type="number",  # Different data type
                page_type="profile",  # Same page type
                ltree_path="test.unique_attribute_duplicate",
                depth=1,
                sort_order=2,
            )
            db_session.add(duplicate_attribute)
            await db_session.commit()

        # Verify the error is about the unique constraint
        error_message = str(exc_info.value)
        assert "unique constraint" in error_message.lower()
        assert "uq_attribute_nodes_mfg_page_name" in error_message

    @pytest.mark.asyncio
    async def test_same_name_different_page_types_allowed(self, db_session: AsyncSession):
        """Test that same attribute name is allowed in different page types."""
        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name="Test Different Page Types",
            description="Test manufacturing type for different page types",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Create attributes with same name in different page types
        page_types = ["profile", "accessories", "glazing"]
        created_attributes = []

        for i, page_type in enumerate(page_types):
            attribute = AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="shared_attribute_name",  # Same name for all
                node_type="attribute",
                data_type="string",
                page_type=page_type,  # Different page types
                ltree_path=f"{page_type}.shared_attribute",
                depth=1,
                sort_order=i + 1,
            )
            db_session.add(attribute)
            created_attributes.append(attribute)

        # This should succeed - no constraint violation
        await db_session.commit()

        # Verify all attributes were created
        for page_type in page_types:
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == manufacturing_type.id,
                AttributeNode.page_type == page_type,
                AttributeNode.name == "shared_attribute_name",
            )
            result = await db_session.execute(stmt)
            attr = result.scalar_one_or_none()
            assert attr is not None, f"Attribute not found for page type {page_type}"
            assert attr.page_type == page_type

    @pytest.mark.asyncio
    async def test_same_name_different_manufacturing_types_allowed(self, db_session: AsyncSession):
        """Test that same attribute name is allowed in different manufacturing types."""
        # Create two manufacturing types
        manufacturing_types = []
        for i in range(2):
            mfg_type = ManufacturingType(
                name=f"Test Manufacturing Type {i + 1}",
                description=f"Test manufacturing type {i + 1}",
                base_category="window",
                base_price=200.00,
                base_weight=15.00,
                is_active=True,
            )
            db_session.add(mfg_type)
            manufacturing_types.append(mfg_type)

        await db_session.commit()
        for mfg_type in manufacturing_types:
            await db_session.refresh(mfg_type)

        # Create attributes with same name and page type in different manufacturing types
        for i, mfg_type in enumerate(manufacturing_types):
            attribute = AttributeNode(
                manufacturing_type_id=mfg_type.id,
                name="common_attribute_name",  # Same name
                node_type="attribute",
                data_type="string",
                page_type="profile",  # Same page type
                ltree_path=f"mfg{i + 1}.common_attribute",
                depth=1,
                sort_order=1,
            )
            db_session.add(attribute)

        # This should succeed - different manufacturing types
        await db_session.commit()

        # Verify both attributes were created
        for mfg_type in manufacturing_types:
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == mfg_type.id,
                AttributeNode.page_type == "profile",
                AttributeNode.name == "common_attribute_name",
            )
            result = await db_session.execute(stmt)
            attr = result.scalar_one_or_none()
            assert attr is not None, f"Attribute not found for manufacturing type {mfg_type.id}"

    @pytest.mark.asyncio
    async def test_setup_script_idempotency_with_constraint(self, db_session: AsyncSession):
        """Test that setup scripts are now properly idempotent due to unique constraint."""
        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name="Test Idempotency Manufacturing Type",
            description="Test manufacturing type for idempotency testing",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Simulate first setup run
        attributes_to_create = [
            {
                "name": "test_attribute_1",
                "node_type": "attribute",
                "data_type": "string",
                "page_type": "profile",
                "ltree_path": "test.attribute1",
                "sort_order": 1,
            },
            {
                "name": "test_attribute_2",
                "node_type": "attribute",
                "data_type": "number",
                "page_type": "profile",
                "ltree_path": "test.attribute2",
                "sort_order": 2,
            },
        ]

        # First run - should succeed
        for attr_def in attributes_to_create:
            attribute = AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name=attr_def["name"],
                node_type=attr_def["node_type"],
                data_type=attr_def["data_type"],
                page_type=attr_def["page_type"],
                ltree_path=attr_def["ltree_path"],
                depth=1,
                sort_order=attr_def["sort_order"],
            )
            db_session.add(attribute)

        await db_session.commit()

        # Count attributes after first run
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == "profile",
        )
        result = await db_session.execute(stmt)
        first_run_count = len(result.scalars().all())
        assert first_run_count == 2

        # Second run - should fail due to unique constraint
        # This simulates what happens when setup script is run twice without proper checks
        for attr_def in attributes_to_create:
            with pytest.raises(IntegrityError):
                attribute = AttributeNode(
                    manufacturing_type_id=manufacturing_type.id,
                    name=attr_def["name"],  # Same name
                    node_type=attr_def["node_type"],
                    data_type=attr_def["data_type"],
                    page_type=attr_def["page_type"],  # Same page type
                    ltree_path=attr_def["ltree_path"] + "_duplicate",
                    depth=1,
                    sort_order=attr_def["sort_order"] + 10,
                )
                db_session.add(attribute)
                await db_session.commit()

        # Count should remain the same
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == "profile",
        )
        result = await db_session.execute(stmt)
        second_run_count = len(result.scalars().all())
        assert second_run_count == first_run_count

    @pytest.mark.parametrize(
        "first_page_type,second_page_type,should_fail",
        [
            ("profile", "profile", True),  # Same page type - should fail
            ("profile", "accessories", False),  # Different page types - should succeed
            ("accessories", "glazing", False),  # Different page types - should succeed
            ("glazing", "profile", False),  # Different page types - should succeed
        ],
        ids=[
            "same_page_type_fails",
            "profile_to_accessories_succeeds",
            "accessories_to_glazing_succeeds",
            "glazing_to_profile_succeeds",
        ],
    )
    @pytest.mark.asyncio
    async def test_page_type_constraint_scenarios(
        self,
        db_session: AsyncSession,
        first_page_type: str,
        second_page_type: str,
        should_fail: bool,
    ):
        """Test various page type constraint scenarios."""
        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name=f"Test Page Type Constraint {first_page_type}-{second_page_type}",
            description="Test manufacturing type for page type constraint testing",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Create first attribute
        first_attribute = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            name="constraint_test_attribute",
            node_type="attribute",
            data_type="string",
            page_type=first_page_type,
            ltree_path=f"{first_page_type}.constraint_test",
            depth=1,
            sort_order=1,
        )
        db_session.add(first_attribute)
        await db_session.commit()

        # Try to create second attribute
        if should_fail:
            with pytest.raises(IntegrityError) as exc_info:
                second_attribute = AttributeNode(
                    manufacturing_type_id=manufacturing_type.id,
                    name="constraint_test_attribute",  # Same name
                    node_type="attribute",
                    data_type="number",
                    page_type=second_page_type,  # Same or different page type
                    ltree_path=f"{second_page_type}.constraint_test",
                    depth=1,
                    sort_order=2,
                )
                db_session.add(second_attribute)
                await db_session.commit()

            # Verify it's the unique constraint error
            error_message = str(exc_info.value)
            assert "unique constraint" in error_message.lower()
        else:
            # Should succeed
            second_attribute = AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="constraint_test_attribute",  # Same name
                node_type="attribute",
                data_type="number",
                page_type=second_page_type,  # Different page type
                ltree_path=f"{second_page_type}.constraint_test",
                depth=1,
                sort_order=2,
            )
            db_session.add(second_attribute)
            await db_session.commit()

            # Verify both attributes exist
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == manufacturing_type.id,
                AttributeNode.name == "constraint_test_attribute",
            )
            result = await db_session.execute(stmt)
            attributes = result.scalars().all()
            assert len(attributes) == 2
            page_types = {attr.page_type for attr in attributes}
            assert page_types == {first_page_type, second_page_type}
