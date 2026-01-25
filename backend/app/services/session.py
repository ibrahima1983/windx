"""Session service for business logic.

This module implements session management business logic including
session creation, validation, and cleanup.

Public Classes:
    SessionService: Session management business logic

Features:
    - Session creation and validation
    - Session cleanup
    - User session management
"""

from __future__ import annotations

from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.session import Session
from app.repositories.session import SessionRepository
from app.services.base import BaseService

__all__ = ["SessionService"]


class SessionService(BaseService):
    """Session service for business logic.

    Handles session management operations including creation, validation,
    and cleanup.

    Attributes:
        db: Database session
        session_repo: Session repository for data access
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize session service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.session_repo = SessionRepository(db)

    async def get_user_sessions(
        self,
        user_id: PositiveInt,
        active_only: bool = False,
    ) -> list[Session]:
        """Get all sessions for a user.

        Args:
            user_id (PositiveInt): User ID
            active_only (bool): Only return active sessions

        Returns:
            list[Session]: List of user sessions
        """
        return await self.session_repo.get_user_sessions(
            user_id=user_id,
            active_only=active_only,
        )

    async def deactivate_session(self, token: str) -> None:
        """Deactivate a session.

        Args:
            token (str): Session token

        Raises:
            NotFoundException: If session not found
        """
        session = await self.session_repo.get_by_token(token)
        if not session:
            raise NotFoundException(
                resource="Session",
                details={"token": "not_found"},
            )

        await self.session_repo.deactivate_session(token)
        await self.commit()

    async def deactivate_all_user_sessions(self, user_id: PositiveInt) -> int:
        """Deactivate all sessions for a user.

        Args:
            user_id (PositiveInt): User ID

        Returns:
            int: Number of sessions deactivated
        """
        sessions = await self.get_user_sessions(user_id, active_only=True)

        for session in sessions:
            await self.session_repo.deactivate_session(session.token)

        await self.commit()
        return len(sessions)

    async def get_active_session(self, token: str) -> Session | None:
        """Get active session by token.

        Args:
            token (str): Session token

        Returns:
            Session | None: Session instance or None if not found/inactive
        """
        return await self.session_repo.get_active_by_token(token)
