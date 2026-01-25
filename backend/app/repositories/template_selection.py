"""TemplateSelection repository for data access.

This module implements the repository pattern for TemplateSelection
data access operations.

Public Classes:
    TemplateSelectionRepository: Repository for template selections

Features:
    - CRUD operations for template selections
    - Bulk operations for selections
    - Query by template or attribute node
"""

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template_selection import TemplateSelection
from app.repositories.base import BaseRepository
from app.schemas.template_selection import (
    TemplateSelectionCreate,
    TemplateSelectionUpdate,
)

__all__ = ["TemplateSelectionRepository"]


class TemplateSelectionRepository(
    BaseRepository[
        TemplateSelection,
        TemplateSelectionCreate,
        TemplateSelectionUpdate,
    ]
):
    """Repository for template selection data access.

    Provides data access methods for template selections including
    CRUD operations, bulk operations, and custom queries.

    Attributes:
        db: Database session
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize template selection repository.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(TemplateSelection, db)

    async def get_by_template(self, template_id: int) -> list[TemplateSelection]:
        """Get all selections for a template.

        Args:
            template_id (int): Template ID

        Returns:
            list[TemplateSelection]: List of selections
        """
        result = await self.db.execute(
            select(TemplateSelection)
            .where(TemplateSelection.template_id == template_id)
            .order_by(TemplateSelection.created_at)
        )
        return list(result.scalars().all())

    async def get_by_attribute_node(self, node_id: int) -> list[TemplateSelection]:
        """Get all selections for an attribute node.

        Args:
            node_id (int): Attribute node ID

        Returns:
            list[TemplateSelection]: List of selections
        """
        result = await self.db.execute(
            select(TemplateSelection)
            .where(TemplateSelection.attribute_node_id == node_id)
            .order_by(TemplateSelection.created_at)
        )
        return list(result.scalars().all())

    async def bulk_create(self, selections: list[dict]) -> list[TemplateSelection]:
        """Create multiple selections in bulk.

        Args:
            selections (list[dict]): List of selection data dictionaries

        Returns:
            list[TemplateSelection]: List of created selections
        """
        created_selections = []
        for selection_data in selections:
            selection = TemplateSelection(**selection_data)
            self.db.add(selection)
            created_selections.append(selection)

        await self.db.flush()
        return created_selections

    async def delete_by_template(self, template_id: int) -> int:
        """Delete all selections for a template.

        Args:
            template_id (int): Template ID

        Returns:
            int: Number of deleted selections
        """
        # noinspection PyTypeChecker
        result: CursorResult = await self.db.execute(
            delete(TemplateSelection).where(TemplateSelection.template_id == template_id)
        )
        return result.rowcount or 0
