"""Session repository for database operations.

This module implements the repository pattern for Session model with
custom query methods for session management and token validation.

Public Classes:
    SessionRepository: Repository for Session CRUD operations

Features:
    - Session lookup by token
    - Active session validation
    - Session expiration checking
    - User session management
    - Session deactivation
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.repositories.base import BaseRepository
from app.schemas.session import SessionCreate

__all__ = ["SessionRepository"]


class SessionRepository(BaseRepository[Session, SessionCreate, dict]):
    """Repository for Session model operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize session repository.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(Session, db)

    async def get_by_token(self, token: str) -> Session | None:
        """Get session by token.

        Args:
            token (str): Session token

        Returns:
            Session | None: Session instance or None if not found
        """
        result = await self.db.execute(select(Session).where(Session.token == token))
        return result.scalar_one_or_none()

    async def get_active_by_token(self, token: str) -> Session | None:
        """Get active session by token.

        Args:
            token (str): Session token

        Returns:
            Session | None: Active session instance or None if not found or expired
        """
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Session).where(
                Session.token == token,
                Session.is_active == True,
                Session.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        user_id: int,
        active_only: bool = False,
    ) -> list[Session]:
        """Get all sessions for a user.

        Args:
            user_id (int): User ID
            active_only (bool): If True, return only active sessions

        Returns:
            list[Session]: List of user sessions
        """
        query = select(Session).where(Session.user_id == user_id)

        if active_only:
            now = datetime.now(UTC)
            query = query.where(
                Session.is_active == True,
                Session.expires_at > now,
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def deactivate_session(self, token: str) -> Session | None:
        """Deactivate a session.

        Args:
            token (str): Session token

        Returns:
            Session | None: Deactivated session or None if not found
        """
        session = await self.get_by_token(token)
        if session:
            session.is_active = False
            await self.db.commit()
            await self.db.refresh(session)
        return session
