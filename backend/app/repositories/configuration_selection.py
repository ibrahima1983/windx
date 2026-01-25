"""ConfigurationSelection repository for data access.

This module implements the repository pattern for ConfigurationSelection
data access operations.

Public Classes:
    ConfigurationSelectionRepository: Repository for configuration selections

Features:
    - CRUD operations for configuration selections
    - Bulk operations for selections
    - Query by configuration or attribute node
    - Price impact calculations
"""

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.engine.cursor import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration_selection import ConfigurationSelection
from app.repositories.base import BaseRepository
from app.schemas.configuration_selection import (
    ConfigurationSelectionCreate,
    ConfigurationSelectionUpdate,
)

__all__ = ["ConfigurationSelectionRepository"]


# noinspection PyTypeChecker
class ConfigurationSelectionRepository(
    BaseRepository[
        ConfigurationSelection,
        ConfigurationSelectionCreate,
        ConfigurationSelectionUpdate,
    ]
):
    """Repository for configuration selection data access.

    Provides data access methods for configuration selections including
    CRUD operations, bulk operations, and custom queries.

    Attributes:
        db: Database session
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize configuration selection repository.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(ConfigurationSelection, db)

    async def get_by_configuration(self, config_id: int) -> list[ConfigurationSelection]:
        """Get all selections for a configuration.

        Args:
            config_id (int): Configuration ID

        Returns:
            list[ConfigurationSelection]: List of selections
        """
        result = await self.db.execute(
            select(ConfigurationSelection)
            .where(ConfigurationSelection.configuration_id == config_id)
            .order_by(ConfigurationSelection.created_at)
        )
        return list(result.scalars().all())

    async def get_by_attribute_node(self, node_id: int) -> list[ConfigurationSelection]:
        """Get all selections for an attribute node.

        Args:
            node_id (int): Attribute node ID

        Returns:
            list[ConfigurationSelection]: List of selections
        """
        result = await self.db.execute(
            select(ConfigurationSelection)
            .where(ConfigurationSelection.attribute_node_id == node_id)
            .order_by(ConfigurationSelection.created_at)
        )
        return list(result.scalars().all())

    async def bulk_create(self, selections: list[dict]) -> list[ConfigurationSelection]:
        """Create multiple selections in bulk.

        Args:
            selections (list[dict]): List of selection data dictionaries

        Returns:
            list[ConfigurationSelection]: List of created selections
        """
        created_selections = []
        for selection_data in selections:
            selection = ConfigurationSelection(**selection_data)
            self.db.add(selection)
            created_selections.append(selection)

        await self.db.flush()
        return created_selections

    # noinspection PyTypeChecker
    async def delete_by_configuration(self, config_id: int) -> int:
        """Delete all selections for a configuration.

        Args:
            config_id (int): Configuration ID

        Returns:
            int: Number of deleted selections
        """
        result = await self.db.execute(
            delete(ConfigurationSelection).where(
                ConfigurationSelection.configuration_id == config_id
            )
        )
        # Cast or assert for type checkers
        cursor_result: CursorResult = result
        return cursor_result.rowcount or 0

    async def get_price_impacts(self, config_id: int) -> list[dict]:
        """Get price impacts for all selections in a configuration.

        Args:
            config_id (int): Configuration ID

        Returns:
            list[dict]: List of price impact data
        """
        result = await self.db.execute(
            select(
                ConfigurationSelection.id,
                ConfigurationSelection.attribute_node_id,
                ConfigurationSelection.calculated_price_impact,
                ConfigurationSelection.calculated_weight_impact,
            ).where(ConfigurationSelection.configuration_id == config_id)
        )
        rows = result.all()
        return [
            {
                "id": row[0],
                "attribute_node_id": row[1],
                "price_impact": row[2] or Decimal("0"),
                "weight_impact": row[3] or Decimal("0"),
            }
            for row in rows
        ]
