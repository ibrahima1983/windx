"""Base service class for business logic.

This module provides the base service class that all service classes
should inherit from.

Public Classes:
    BaseService: Base class for all services

Features:
    - Database session management
    - Common service patterns
    - Transaction handling
"""

from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["BaseService"]


class BaseService:
    """Base service class for business logic.

    Provides common functionality for all service classes including
    database session management and transaction handling.

    Attributes:
        db: Database session for operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize base service.

        Args:
            db (AsyncSession): Database session
        """
        self.db = db

    async def commit(self) -> None:
        """Commit current transaction.

        Raises:
            DatabaseException: If commit fails
        """
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            from app.core.exceptions import DatabaseException

            # Log the actual error for debugging
            print(f"[ERROR] Commit failed: {type(e).__name__}: {str(e)}")
            import traceback

            traceback.print_exc()

            raise DatabaseException(
                message="Failed to commit transaction",
                details={"error": str(e), "type": type(e).__name__},
            )

    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.db.rollback()

    async def refresh(self, instance) -> None:
        """Refresh instance from database.

        Args:
            instance: SQLAlchemy model instance to refresh
        """
        await self.db.refresh(instance)
