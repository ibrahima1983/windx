"""Repository for ConfigurationTemplate operations.

This module provides the repository implementation for ConfigurationTemplate
model with custom query methods.

Public Classes:
    ConfigurationTemplateRepository: Repository for template operations

Features:
    - Standard CRUD operations via BaseRepository
    - Get public templates
    - Get by manufacturing type
    - Increment usage count
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration_template import ConfigurationTemplate
from app.repositories.base import BaseRepository
from app.schemas.configuration_template import (
    ConfigurationTemplateCreate,
    ConfigurationTemplateUpdate,
)

__all__ = ["ConfigurationTemplateRepository"]


# noinspection PyTypeChecker
class ConfigurationTemplateRepository(
    BaseRepository[
        ConfigurationTemplate,
        ConfigurationTemplateCreate,
        ConfigurationTemplateUpdate,
    ]
):
    """Repository for ConfigurationTemplate operations.

    Provides data access methods for configuration templates including
    filtering by visibility, manufacturing type, and usage tracking.

    Attributes:
        model: ConfigurationTemplate model class
        db: Database session
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with ConfigurationTemplate model.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(ConfigurationTemplate, db)

    async def get_public_templates(self) -> list[ConfigurationTemplate]:
        """Get all public templates.

        Returns only templates where is_public is True and is_active is True,
        ordered by usage count (most popular first).

        Returns:
            list[ConfigurationTemplate]: List of public templates

        Example:
            ```python
            public_templates = await repo.get_public_templates()
            ```
        """
        result = await self.db.execute(
            select(ConfigurationTemplate)
            .where(ConfigurationTemplate.is_public == True)
            .where(ConfigurationTemplate.is_active)
            .order_by(ConfigurationTemplate.usage_count.desc())
        )
        return list(result.scalars().all())

    async def get_by_manufacturing_type(
        self, manufacturing_type_id: int
    ) -> list[ConfigurationTemplate]:
        """Get templates by manufacturing type.

        Returns all active templates for the specified manufacturing type,
        ordered by usage count (most popular first).

        Args:
            manufacturing_type_id (int): Manufacturing type ID

        Returns:
            list[ConfigurationTemplate]: List of templates

        Example:
            ```python
            window_templates = await repo.get_by_manufacturing_type(1)
            ```
        """
        result = await self.db.execute(
            select(ConfigurationTemplate)
            .where(ConfigurationTemplate.manufacturing_type_id == manufacturing_type_id)
            .where(ConfigurationTemplate.is_active)
            .order_by(ConfigurationTemplate.usage_count.desc())
        )
        return list(result.scalars().all())

    async def increment_usage_count(self, template_id: int) -> None:
        """Increment the usage count for a template.

        Atomically increments the usage_count field by 1.
        This is called when a template is applied to create a configuration.

        Args:
            template_id (int): Template ID

        Example:
            ```python
            await repo.increment_usage_count(42)
            ```
        """
        await self.db.execute(
            update(ConfigurationTemplate)
            .where(ConfigurationTemplate.id == template_id)
            .values(usage_count=ConfigurationTemplate.usage_count + 1)
        )
        await self.db.commit()

    async def get_popular(
        self,
        limit: int = 10,
        manufacturing_type_id: int | None = None,
    ) -> list[ConfigurationTemplate]:
        """Get most popular templates by usage count.

        Returns the most popular templates (highest usage_count) that are
        both public and active. Optionally filters by manufacturing type.

        Args:
            limit (int): Maximum number of templates to return (default: 10)
            manufacturing_type_id (int | None): Optional filter by manufacturing type

        Returns:
            list[ConfigurationTemplate]: List of templates ordered by usage_count descending

        Example:
            ```python
            # Get top 5 popular templates
            popular = await repo.get_popular(limit=5)

            # Get top 10 popular window templates
            window_popular = await repo.get_popular(limit=10, manufacturing_type_id=1)
            ```
        """
        stmt = (
            select(ConfigurationTemplate)
            .where(ConfigurationTemplate.is_active == True)
            .where(ConfigurationTemplate.is_public == True)
            .order_by(ConfigurationTemplate.usage_count.desc())
            .limit(limit)
        )

        if manufacturing_type_id is not None:
            stmt = stmt.where(ConfigurationTemplate.manufacturing_type_id == manufacturing_type_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def get_filtered(
        is_public: bool | None = None,
        manufacturing_type_id: int | None = None,
        template_type: str | None = None,
        is_active: bool | None = None,
    ):
        """Build filtered query for templates.

        Args:
            is_public (bool | None): Filter by public visibility
            manufacturing_type_id (int | None): Filter by manufacturing type
            template_type (str | None): Filter by template type
            is_active (bool | None): Filter by active status

        Returns:
            Select: SQLAlchemy select statement
        """
        from sqlalchemy import Select, select

        query: Select = select(ConfigurationTemplate)

        if is_public is not None:
            query = query.where(ConfigurationTemplate.is_public == is_public)

        if manufacturing_type_id is not None:
            query = query.where(
                ConfigurationTemplate.manufacturing_type_id == manufacturing_type_id
            )

        if template_type:
            query = query.where(ConfigurationTemplate.template_type == template_type)

        if is_active is not None:
            query = query.where(ConfigurationTemplate.is_active == is_active)

        query = query.order_by(ConfigurationTemplate.usage_count.desc())

        return query

    async def get_with_selections(self, template_id: int) -> ConfigurationTemplate | None:
        """Get template with selections loaded.

        Loads the template along with all its selections and their
        attribute nodes in a single query to prevent N+1 problems.

        Args:
            template_id (int): Template ID

        Returns:
            ConfigurationTemplate | None: Template with selections or None

        Example:
            ```python
            # Get template with all selections loaded
            template = await repo.get_with_selections(42)
            if template:
                for selection in template.selections:
                    print(f"{selection.attribute_node.name}: {selection.string_value}")
            ```
        """
        from sqlalchemy.orm import selectinload

        from app.models.template_selection import TemplateSelection

        result = await self.db.execute(
            select(ConfigurationTemplate)
            .where(ConfigurationTemplate.id == template_id)
            .options(
                selectinload(ConfigurationTemplate.selections).selectinload(
                    TemplateSelection.attribute_node
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_with_full_details(self, template_id: int) -> ConfigurationTemplate | None:
        """Get template with all related data eager-loaded.

        Loads the template along with:
        - Manufacturing type
        - Creator user
        - All selections with their attribute nodes

        Args:
            template_id (int): Template ID

        Returns:
            ConfigurationTemplate | None: Template with full details or None

        Example:
            ```python
            # Get template with all related data
            template = await repo.get_with_full_details(42)
            if template:
                print(f"Type: {template.manufacturing_type.name}")
                print(f"Creator: {template.creator.email}")
                print(f"Selections: {len(template.selections)}")
            ```
        """
        from sqlalchemy.orm import selectinload

        from app.models.template_selection import TemplateSelection

        result = await self.db.execute(
            select(ConfigurationTemplate)
            .where(ConfigurationTemplate.id == template_id)
            .options(
                selectinload(ConfigurationTemplate.manufacturing_type),
                selectinload(ConfigurationTemplate.creator),
                selectinload(ConfigurationTemplate.selections).selectinload(
                    TemplateSelection.attribute_node
                ),
            )
        )
        return result.scalar_one_or_none()
