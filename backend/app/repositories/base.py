"""Base repository with common CRUD operations.

This module provides a generic base repository class implementing the
repository pattern for database operations with type safety.

Public Classes:
    BaseRepository: Generic repository with CRUD operations

Features:
    - Generic type-safe repository pattern
    - Common CRUD operations (Create, Read, Update, Delete)
    - Pagination support
    - Async SQLAlchemy operations
    - Pydantic schema integration
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, PositiveInt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

__all__ = ["BaseRepository", "ModelType", "CreateSchemaType", "UpdateSchemaType"]


# noinspection PyTypeChecker
class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository class with common CRUD operations.

    Attributes:
        model: SQLAlchemy model class
        db: Database session
    """

    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        """Initialize repository.

        Args:
            model (type[ModelType]): SQLAlchemy model class
            db (AsyncSession): Database session
        """
        self.model = model
        self.db = db

    async def get(self, id: PositiveInt) -> ModelType | None:
        """Get a single record by ID.

        Args:
            id (PositiveInt): Record ID

        Returns:
            ModelType | None: Model instance or None if not found
        """
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get multiple records with pagination.

        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return

        Returns:
            list[ModelType]: List of model instances
        """
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record.

        Args:
            obj_in (CreateSchemaType): Schema with data for creation

        Returns:
            ModelType: Created model instance
        """
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update an existing record.

        Args:
            db_obj (ModelType): Existing model instance
            obj_in (UpdateSchemaType | dict[str, Any]): Schema or dict with update data

        Returns:
            ModelType: Updated model instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: PositiveInt) -> ModelType | None:
        """Delete a record by ID.

        Args:
            id (PositiveInt): Record ID

        Returns:
            ModelType | None: Deleted model instance or None if not found
        """
        db_obj = await self.get(id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.commit()
        return db_obj

    async def get_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> ModelType | None:
        """Get a single record by any field name.

        Args:
            field_name (str): Name of the model field to filter by
            value (Any): Value to match

        Returns:
            ModelType | None: Model instance or None if not found

        Raises:
            ValueError: If field_name is not a valid model attribute

        Example:
            user = await repo.get_by_field("email", "user@example.com")
        """
        # Validate field exists on model
        if not hasattr(self.model, field_name):
            raise ValueError(f"Invalid field name: {field_name}")

        stmt = select(self.model).where(getattr(self.model, field_name) == value)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, id: PositiveInt) -> bool:
        """Check if a record exists by ID.

        Args:
            id (PositiveInt): Primary key value

        Returns:
            bool: True if record exists, False otherwise

        Example:
            if await repo.exists(123):
                print("Record found")
        """
        from sqlalchemy import func as sql_func

        stmt = select(sql_func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def count(
        self,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count records with optional filters.

        Args:
            filters (dict[str, Any] | None): Dictionary of field names to values

        Returns:
            int: Count of matching records

        Example:
            active_count = await repo.count({"is_active": True})
        """
        from sqlalchemy import func as sql_func

        stmt = select(sql_func.count()).select_from(self.model)

        if filters:
            for field_name, filter_value in filters.items():
                # Validate field exists on model
                if not hasattr(self.model, field_name):
                    raise ValueError(f"Invalid field name: {field_name}")
                stmt = stmt.where(getattr(self.model, field_name) == filter_value)

        result = await self.db.execute(stmt)
        return result.scalar_one()
