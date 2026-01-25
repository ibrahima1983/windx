"""Repository for ManufacturingType operations.

This module provides the repository implementation for ManufacturingType
model with custom query methods.

Public Classes:
    ManufacturingTypeRepository: Repository for manufacturing type operations

Features:
    - Standard CRUD operations via BaseRepository
    - Get by name lookup
    - Get active manufacturing types
    - Get by category filtering
    - Filtered queries with sorting
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy import Select, asc, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manufacturing_type import ManufacturingType
from app.repositories.base import BaseRepository
from app.schemas.manufacturing_type import (
    ManufacturingTypeCreate,
    ManufacturingTypeUpdate,
)

__all__ = ["ManufacturingTypeRepository"]


class ManufacturingTypeRepository(
    BaseRepository[ManufacturingType, ManufacturingTypeCreate, ManufacturingTypeUpdate]
):
    """Repository for ManufacturingType operations.

    Provides data access methods for manufacturing types including
    lookups by name, category, and active status.

    Attributes:
        model: ManufacturingType model class
        db: Database session
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with ManufacturingType model.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(ManufacturingType, db)

    async def get_by_name(self, name: str) -> ManufacturingType | None:
        """Get manufacturing type by name.

        Args:
            name (str): Manufacturing type name

        Returns:
            ManufacturingType | None: Manufacturing type or None if not found

        Example:
            ```python
            window_type = await repo.get_by_name("Casement Window")
            ```
        """
        result = await self.db.execute(
            select(ManufacturingType).where(ManufacturingType.name == name)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> list[ManufacturingType]:
        """Get all active manufacturing types.

        Returns only manufacturing types where is_active is True,
        ordered by name.

        Returns:
            list[ManufacturingType]: List of active manufacturing types

        Example:
            ```python
            active_types = await repo.get_active()
            ```
        """
        result = await self.db.execute(
            select(ManufacturingType)
            .where(ManufacturingType.is_active == True)
            .order_by(ManufacturingType.name)
        )
        return list(result.scalars().all())

    async def get_by_category(self, category: str) -> list[ManufacturingType]:
        """Get manufacturing types by base category.

        Filters manufacturing types by their base_category field
        (e.g., "window", "door", "furniture").

        Args:
            category (str): Base category name

        Returns:
            list[ManufacturingType]: List of manufacturing types in category

        Example:
            ```python
            windows = await repo.get_by_category("window")
            doors = await repo.get_by_category("door")
            ```
        """
        result = await self.db.execute(
            select(ManufacturingType)
            .where(ManufacturingType.base_category == category)
            .order_by(ManufacturingType.name)
        )
        return list(result.scalars().all())

    @staticmethod
    def get_filtered(
        is_active: bool | None = None,
        base_category: str | None = None,
        search: str | None = None,
        sort_by: Literal["created_at", "name", "base_price"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> Select:
        """Build filtered query for manufacturing types.

        Creates a SQLAlchemy Select statement with optional filters and sorting.
        This method returns a query that can be paginated.

        Args:
            is_active (bool | None): Filter by active status
            base_category (str | None): Filter by base category
            search (str | None): Search in name or description
            sort_by (Literal): Column to sort by
            sort_order (Literal): Sort direction

        Returns:
            Select: SQLAlchemy select statement

        Example:
            ```python
            query = repo.get_filtered(
                is_active=True,
                base_category="window",
                search="casement",
                sort_by="name",
                sort_order="asc"
            )
            result = await db.execute(query)
            types = result.scalars().all()
            ```
        """
        query = select(ManufacturingType)

        # Apply filters
        if is_active is not None:
            query = query.where(ManufacturingType.is_active == is_active)

        if base_category:
            query = query.where(ManufacturingType.base_category == base_category)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    ManufacturingType.name.ilike(search_term),
                    ManufacturingType.description.ilike(search_term),
                )
            )

        # Apply sorting
        sort_column = getattr(ManufacturingType, sort_by)
        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        return query
