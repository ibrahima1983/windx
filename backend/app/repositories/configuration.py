"""Repository for Configuration operations.

This module provides the repository implementation for Configuration
model with custom query methods and eager loading support.

Public Classes:
    ConfigurationRepository: Repository for configuration operations

Features:
    - Standard CRUD operations via BaseRepository
    - Get by customer with optional status filter
    - Get by status
    - Eager loading of selections
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.configuration import Configuration
from app.repositories.base import BaseRepository
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate

__all__ = ["ConfigurationRepository"]


# noinspection PyTypeChecker
class ConfigurationRepository(
    BaseRepository[Configuration, ConfigurationCreate, ConfigurationUpdate]
):
    """Repository for Configuration operations.

    Provides data access methods for configurations including
    filtering by customer, status, and eager loading of selections.

    Attributes:
        model: Configuration model class
        db: Database session
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with Configuration model.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(Configuration, db)

    async def get_by_customer(
        self, customer_id: int, status: str | None = None
    ) -> list[Configuration]:
        """Get configurations by customer with optional status filter.

        Returns all configurations for a specific customer, optionally
        filtered by status. Results are ordered by creation date (newest first).

        Args:
            customer_id (int): Customer ID
            status (str | None): Optional status filter (draft, saved, quoted, ordered)

        Returns:
            list[Configuration]: List of configurations

        Example:
            ```python
            # Get all configurations for customer
            configs = await repo.get_by_customer(42)

            # Get only quoted configurations
            quoted = await repo.get_by_customer(42, status="quoted")
            ```
        """
        query = select(Configuration).where(Configuration.customer_id == customer_id)

        if status is not None:
            query = query.where(Configuration.status == status)

        query = query.order_by(Configuration.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[Configuration]:
        """Get configurations by status.

        Returns all configurations with the specified status,
        ordered by creation date (newest first).

        Args:
            status (str): Configuration status (draft, saved, quoted, ordered)

        Returns:
            list[Configuration]: List of configurations

        Example:
            ```python
            # Get all draft configurations
            drafts = await repo.get_by_status("draft")

            # Get all ordered configurations
            orders = await repo.get_by_status("ordered")
            ```
        """
        result = await self.db.execute(
            select(Configuration)
            .where(Configuration.status == status)
            .order_by(Configuration.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_with_selections(self, config_id: int) -> Configuration | None:
        """Get configuration with eager-loaded selections.

        Loads the configuration along with all its selections in a single
        query to prevent N+1 query problems. Also loads related attribute
        nodes for each selection.

        Args:
            config_id (int): Configuration ID

        Returns:
            Configuration | None: Configuration with selections or None if not found

        Example:
            ```python
            # Get configuration with all selections loaded
            config = await repo.get_with_selections(42)
            if config:
                for selection in config.selections:
                    print(f"{selection.attribute_node.name}: {selection.string_value}")
            ```
        """
        from app.models.configuration_selection import ConfigurationSelection

        result = await self.db.execute(
            select(Configuration)
            .where(Configuration.id == config_id)
            .options(
                selectinload(Configuration.selections).selectinload(
                    ConfigurationSelection.attribute_node
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_with_full_details(self, config_id: int) -> Configuration | None:
        """Get configuration with all related data eager-loaded.

        Loads the configuration along with:
        - Manufacturing type
        - Customer
        - All selections with their attribute nodes
        - All quotes

        Args:
            config_id (int): Configuration ID

        Returns:
            Configuration | None: Configuration with full details or None if not found

        Example:
            ```python
            # Get configuration with all related data
            config = await repo.get_with_full_details(42)
            if config:
                print(f"Type: {config.manufacturing_type.name}")
                print(f"Customer: {config.customer.email}")
                print(f"Selections: {len(config.selections)}")
                print(f"Quotes: {len(config.quotes)}")
            ```
        """
        from app.models.configuration_selection import ConfigurationSelection

        result = await self.db.execute(
            select(Configuration)
            .where(Configuration.id == config_id)
            .options(
                selectinload(Configuration.manufacturing_type),
                selectinload(Configuration.customer),
                selectinload(Configuration.selections).selectinload(
                    ConfigurationSelection.attribute_node
                ),
                selectinload(Configuration.quotes),
            )
        )
        return result.scalar_one_or_none()
