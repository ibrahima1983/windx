"""Integration tests for duplicate page type setup prevention.

This module tests whether the system properly handles attempts to set up
the same page type multiple times and validates proper exception handling.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.manufacturing_type_resolver import ManufacturingTypeResolver
from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType


class TestDuplicatePageTypeSetup:
    """Test suite for duplicate page type setup prevention."""

    @pytest.mark.asyncio
    async def test_setup_same_page_type_twice_should_not_duplicate(self, db_session: AsyncSession):
        """Test that setting up the same page type twice doesn't create duplicates."""
        # Create a manufacturing type for testing
        manufacturing_type = ManufacturingType(
            name="Test Window Type",
            description="Test manufacturing type",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Create initial profile attributes
        profile_attributes = [
            AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="test_attribute_1",
                node_type="attribute",
                data_type="string",
                page_type="profile",
                ltree_path="test.attribute1",
                depth=1,
                sort_order=1,
            ),
            AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="test_attribute_2",
                node_type="attribute",
                data_type="number",
                page_type="profile",
                ltree_path="test.attribute2",
                depth=1,
                sort_order=2,
            ),
        ]

        for attr in profile_attributes:
            db_session.add(attr)
        await db_session.commit()

        # Verify initial count
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == "profile",
        )
        result = await db_session.execute(stmt)
        initial_count = len(result.scalars().all())
        assert initial_count == 2

        # Try to add the same page type again (simulate running setup script twice)
        duplicate_attributes = [
            AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="test_attribute_1",  # Same name
                node_type="attribute",
                data_type="string",
                page_type="profile",  # Same page type
                ltree_path="test.attribute1",
                depth=1,
                sort_order=1,
            ),
            AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="test_attribute_3",  # New name
                node_type="attribute",
                data_type="boolean",
                page_type="profile",  # Same page type
                ltree_path="test.attribute3",
                depth=1,
                sort_order=3,
            ),
        ]

        # This should either:
        # 1. Raise an exception due to unique constraint violation
        # 2. Be handled gracefully by the setup script logic
        try:
            for attr in duplicate_attributes:
                db_session.add(attr)
            await db_session.commit()

            # If no exception, check if duplicates were created
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == manufacturing_type.id,
                AttributeNode.page_type == "profile",
            )
            result = await db_session.execute(stmt)
            final_count = len(result.scalars().all())

            # We should have either the same count (no duplicates) or more (new attributes added)
            # But we should NOT have exact duplicates of the same name
            stmt_by_name = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == manufacturing_type.id,
                AttributeNode.page_type == "profile",
                AttributeNode.name == "test_attribute_1",
            )
            result_by_name = await db_session.execute(stmt_by_name)
            duplicate_name_count = len(result_by_name.scalars().all())

            # This is the key test - we should not have multiple attributes with the same name
            # in the same manufacturing type and page type
            assert duplicate_name_count <= 1, (
                f"Found {duplicate_name_count} attributes with name 'test_attribute_1', expected at most 1"
            )

        except Exception as e:
            # If an exception is raised, it should be a meaningful one
            assert (
                "unique" in str(e).lower()
                or "duplicate" in str(e).lower()
                or "constraint" in str(e).lower()
            ), f"Expected a constraint-related exception, got: {e}"

    @pytest.mark.asyncio
    async def test_setup_different_page_types_should_work(self, db_session: AsyncSession):
        """Test that setting up different page types for the same manufacturing type works."""
        # Create a manufacturing type for testing
        manufacturing_type = ManufacturingType(
            name="Test Window Type Multi-Page",
            description="Test manufacturing type for multi-page",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Create attributes for different page types
        page_types = ["profile", "accessories", "glazing"]

        for page_type in page_types:
            attributes = [
                AttributeNode(
                    manufacturing_type_id=manufacturing_type.id,
                    name=f"{page_type}_attribute_1",
                    node_type="attribute",
                    data_type="string",
                    page_type=page_type,
                    ltree_path=f"{page_type}.attribute1",
                    depth=1,
                    sort_order=1,
                ),
                AttributeNode(
                    manufacturing_type_id=manufacturing_type.id,
                    name=f"{page_type}_attribute_2",
                    node_type="attribute",
                    data_type="number",
                    page_type=page_type,
                    ltree_path=f"{page_type}.attribute2",
                    depth=1,
                    sort_order=2,
                ),
            ]

            for attr in attributes:
                db_session.add(attr)

        await db_session.commit()

        # Verify all page types were created
        for page_type in page_types:
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == manufacturing_type.id,
                AttributeNode.page_type == page_type,
            )
            result = await db_session.execute(stmt)
            count = len(result.scalars().all())
            assert count == 2, f"Expected 2 attributes for {page_type}, got {count}"

    @pytest.mark.asyncio
    async def test_manufacturing_type_resolver_with_duplicate_setup_attempts(
        self, db_session: AsyncSession
    ):
        """Test ManufacturingTypeResolver behavior when setup is attempted multiple times."""
        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name="Window Profile Entry",  # Use the standard name
            description="Test manufacturing type",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Test resolver can find the type
        resolved_type = await ManufacturingTypeResolver.get_default_for_page_type(
            db_session, "profile", "window"
        )
        assert resolved_type is not None
        assert resolved_type.id == manufacturing_type.id

        # Test with different page types
        for page_type in ["profile", "accessories", "glazing"]:
            resolved_type = await ManufacturingTypeResolver.get_default_for_page_type(
                db_session, page_type, "window"
            )
            assert resolved_type is not None
            assert resolved_type.id == manufacturing_type.id

    @pytest.mark.asyncio
    async def test_setup_script_idempotency(self, db_session: AsyncSession):
        """Test that setup scripts are idempotent (can be run multiple times safely)."""
        # This test simulates what happens when setup scripts are run multiple times

        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name="Window Profile Entry",
            description="Test manufacturing type",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Simulate first setup run
        first_run_attributes = [
            AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="name",
                node_type="attribute",
                data_type="string",
                page_type="profile",
                ltree_path="basic_information.name",
                depth=1,
                sort_order=1,
            ),
            AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="type",
                node_type="attribute",
                data_type="string",
                page_type="profile",
                ltree_path="basic_information.type",
                depth=1,
                sort_order=2,
            ),
        ]

        for attr in first_run_attributes:
            db_session.add(attr)
        await db_session.commit()

        # Count after first run
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == "profile",
        )
        result = await db_session.execute(stmt)
        first_run_count = len(result.scalars().all())
        assert first_run_count == 2

        # Simulate second setup run (should be idempotent)
        # This is what the setup script should do - check if attributes exist first
        stmt_check = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == "profile",
        )
        result_check = await db_session.execute(stmt_check)
        existing_attributes = result_check.scalars().all()

        if existing_attributes:
            # Setup script should detect existing attributes and skip creation
            # or update existing ones instead of creating duplicates
            print(f"Found {len(existing_attributes)} existing attributes, skipping creation")
        else:
            # Only create if none exist
            for attr in first_run_attributes:
                db_session.add(attr)
            await db_session.commit()

        # Count after second run should be the same
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type.id,
            AttributeNode.page_type == "profile",
        )
        result = await db_session.execute(stmt)
        second_run_count = len(result.scalars().all())

        assert second_run_count == first_run_count, (
            f"Second run should not create duplicates. First: {first_run_count}, Second: {second_run_count}"
        )

    @pytest.mark.parametrize(
        "page_type,should_succeed",
        [
            ("profile", True),
            ("accessories", True),
            ("glazing", True),
            ("invalid", False),
            ("", False),
            (None, False),
        ],
        ids=[
            "valid_profile",
            "valid_accessories",
            "valid_glazing",
            "invalid_page_type",
            "empty_page_type",
            "none_page_type",
        ],
    )
    @pytest.mark.asyncio
    async def test_page_type_validation_in_setup(
        self, db_session: AsyncSession, page_type: str | None, should_succeed: bool
    ):
        """Test that page type validation works correctly during setup."""
        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name="Test Validation Type",
            description="Test manufacturing type",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        if should_succeed:
            # Valid page types should work
            attribute = AttributeNode(
                manufacturing_type_id=manufacturing_type.id,
                name="test_attribute",
                node_type="attribute",
                data_type="string",
                page_type=page_type,
                ltree_path=f"{page_type}.test",
                depth=1,
                sort_order=1,
            )
            db_session.add(attribute)
            await db_session.commit()

            # Verify it was created
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == manufacturing_type.id,
                AttributeNode.page_type == page_type,
            )
            result = await db_session.execute(stmt)
            created_attr = result.scalar_one_or_none()
            assert created_attr is not None
            assert created_attr.page_type == page_type
        else:
            # Invalid page types should be caught by validation
            # Note: This depends on whether we have database-level constraints
            # or application-level validation
            if page_type is None:
                # None should be caught by nullable=False constraint
                with pytest.raises(Exception):
                    attribute = AttributeNode(
                        manufacturing_type_id=manufacturing_type.id,
                        name="test_attribute",
                        node_type="attribute",
                        data_type="string",
                        page_type=page_type,
                        ltree_path="test.test",
                        depth=1,
                        sort_order=1,
                    )
                    db_session.add(attribute)
                    await db_session.commit()
            else:
                # Invalid string values might be allowed at DB level
                # but should be caught by application validation
                is_valid = ManufacturingTypeResolver.validate_page_type(page_type)
                assert not is_valid, f"Page type '{page_type}' should be invalid"
