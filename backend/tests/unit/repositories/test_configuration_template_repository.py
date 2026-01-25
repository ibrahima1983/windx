"""Unit tests for ConfigurationTemplateRepository.

Tests the get_popular method added to ConfigurationTemplateRepository:
- get_popular: Get most popular templates by usage count
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration_template import ConfigurationTemplate
from app.models.manufacturing_type import ManufacturingType
from app.repositories.configuration_template import ConfigurationTemplateRepository


@pytest.mark.asyncio
class TestConfigurationTemplateRepositoryGetPopular:
    """Test get_popular method."""

    async def test_get_popular_returns_templates_ordered_by_usage_count(
        self, db_session: AsyncSession
    ):
        """Test get_popular returns templates ordered by usage_count descending."""
        # Arrange
        mfg_type = ManufacturingType(
            name="Test Window",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        template1 = ConfigurationTemplate(
            name="Template 1",
            manufacturing_type_id=mfg_type.id,
            is_public=True,
            is_active=True,
            usage_count=10,
        )
        template2 = ConfigurationTemplate(
            name="Template 2",
            manufacturing_type_id=mfg_type.id,
            is_public=True,
            is_active=True,
            usage_count=50,
        )
        template3 = ConfigurationTemplate(
            name="Template 3",
            manufacturing_type_id=mfg_type.id,
            is_public=True,
            is_active=True,
            usage_count=25,
        )
        db_session.add_all([template1, template2, template3])
        await db_session.commit()

        repo = ConfigurationTemplateRepository(db_session)

        # Act
        popular = await repo.get_popular(limit=10)

        # Assert
        assert len(popular) == 3
        assert popular[0].name == "Template 2"  # usage_count=50
        assert popular[1].name == "Template 3"  # usage_count=25
        assert popular[2].name == "Template 1"  # usage_count=10

    async def test_get_popular_respects_limit(self, db_session: AsyncSession):
        """Test get_popular respects the limit parameter."""
        # Arrange
        mfg_type = ManufacturingType(
            name="Test Window",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        templates = [
            ConfigurationTemplate(
                name=f"Template {i}",
                manufacturing_type_id=mfg_type.id,
                is_public=True,
                is_active=True,
                usage_count=i * 10,
            )
            for i in range(1, 6)
        ]
        db_session.add_all(templates)
        await db_session.commit()

        repo = ConfigurationTemplateRepository(db_session)

        # Act
        popular = await repo.get_popular(limit=3)

        # Assert
        assert len(popular) == 3
        assert popular[0].usage_count == 50  # Template 5
        assert popular[1].usage_count == 40  # Template 4
        assert popular[2].usage_count == 30  # Template 3

    async def test_get_popular_filters_by_manufacturing_type(self, db_session: AsyncSession):
        """Test get_popular filters by manufacturing_type_id when provided."""
        # Arrange
        mfg_type1 = ManufacturingType(
            name="Window",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
        )
        mfg_type2 = ManufacturingType(
            name="Door",
            base_category="door",
            base_price=300.00,
            base_weight=25.00,
        )
        db_session.add_all([mfg_type1, mfg_type2])
        await db_session.commit()
        await db_session.refresh(mfg_type1)
        await db_session.refresh(mfg_type2)

        window_template = ConfigurationTemplate(
            name="Window Template",
            manufacturing_type_id=mfg_type1.id,
            is_public=True,
            is_active=True,
            usage_count=30,
        )
        door_template = ConfigurationTemplate(
            name="Door Template",
            manufacturing_type_id=mfg_type2.id,
            is_public=True,
            is_active=True,
            usage_count=50,
        )
        db_session.add_all([window_template, door_template])
        await db_session.commit()

        repo = ConfigurationTemplateRepository(db_session)

        # Act
        window_popular = await repo.get_popular(limit=10, manufacturing_type_id=mfg_type1.id)

        # Assert
        assert len(window_popular) == 1
        assert window_popular[0].name == "Window Template"
        assert window_popular[0].manufacturing_type_id == mfg_type1.id

    async def test_get_popular_excludes_inactive_templates(self, db_session: AsyncSession):
        """Test get_popular excludes templates where is_active is False."""
        # Arrange
        mfg_type = ManufacturingType(
            name="Test Window",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        active_template = ConfigurationTemplate(
            name="Active Template",
            manufacturing_type_id=mfg_type.id,
            is_public=True,
            is_active=True,
            usage_count=30,
        )
        inactive_template = ConfigurationTemplate(
            name="Inactive Template",
            manufacturing_type_id=mfg_type.id,
            is_public=True,
            is_active=False,
            usage_count=50,
        )
        db_session.add_all([active_template, inactive_template])
        await db_session.commit()

        repo = ConfigurationTemplateRepository(db_session)

        # Act
        popular = await repo.get_popular(limit=10)

        # Assert
        assert len(popular) == 1
        assert popular[0].name == "Active Template"

    async def test_get_popular_excludes_private_templates(self, db_session: AsyncSession):
        """Test get_popular excludes templates where is_public is False."""
        # Arrange
        mfg_type = ManufacturingType(
            name="Test Window",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        public_template = ConfigurationTemplate(
            name="Public Template",
            manufacturing_type_id=mfg_type.id,
            is_public=True,
            is_active=True,
            usage_count=30,
        )
        private_template = ConfigurationTemplate(
            name="Private Template",
            manufacturing_type_id=mfg_type.id,
            is_public=False,
            is_active=True,
            usage_count=50,
        )
        db_session.add_all([public_template, private_template])
        await db_session.commit()

        repo = ConfigurationTemplateRepository(db_session)

        # Act
        popular = await repo.get_popular(limit=10)

        # Assert
        assert len(popular) == 1
        assert popular[0].name == "Public Template"

    async def test_get_popular_returns_empty_list_when_no_templates(self, db_session: AsyncSession):
        """Test get_popular returns empty list when no templates exist."""
        # Arrange
        repo = ConfigurationTemplateRepository(db_session)

        # Act
        popular = await repo.get_popular(limit=10)

        # Assert
        assert len(popular) == 0
        assert popular == []

    async def test_get_popular_default_limit_is_10(self, db_session: AsyncSession):
        """Test get_popular uses default limit of 10 when not specified."""
        # Arrange
        mfg_type = ManufacturingType(
            name="Test Window",
            base_category="window",
            base_price=200.00,
            base_weight=15.00,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        templates = [
            ConfigurationTemplate(
                name=f"Template {i}",
                manufacturing_type_id=mfg_type.id,
                is_public=True,
                is_active=True,
                usage_count=i * 10,
            )
            for i in range(1, 16)  # Create 15 templates
        ]
        db_session.add_all(templates)
        await db_session.commit()

        repo = ConfigurationTemplateRepository(db_session)

        # Act
        popular = await repo.get_popular()  # No limit specified

        # Assert
        assert len(popular) == 10  # Default limit
