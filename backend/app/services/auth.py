"""Authentication service for business logic.

This module implements authentication and authorization business logic
including login, token generation, and password verification.

Public Classes:
    AuthService: Authentication business logic

Features:
    - User authentication
    - Token generation and validation
    - Password verification
    - Session management integration
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationException
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.schemas.session import SessionCreate
from app.services.base import BaseService

__all__ = ["AuthService"]


class AuthService(BaseService):
    """Authentication service for business logic.

    Handles authentication operations including login, token generation,
    and session management.

    Attributes:
        db: Database session
        user_repo: User repository for data access
        session_repo: Session repository for session management
        settings: Application settings
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize auth service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)
        self.settings = get_settings()

    async def authenticate_user(self, username_or_email: str, password: str) -> User:
        """Authenticate user with username/email and password.

        Args:
            username_or_email (str): User email or username
            password (str): Plain text password

        Returns:
            User: Authenticated user instance

        Raises:
            AuthenticationException: If authentication fails
        """
        # Try to find user by username first, then email
        user = await self.user_repo.get_by_username(username_or_email)
        if not user:
            user = await self.user_repo.get_by_email(username_or_email)

        if not user:
            raise AuthenticationException(
                message="Invalid username/email or password",
                details={"username_or_email": username_or_email},
            )

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise AuthenticationException(
                message="Invalid username/email or password",
                details={"username_or_email": username_or_email},
            )

        # Check if user is active
        if not user.is_active:
            raise AuthenticationException(
                message="User account is inactive",
                details={"username_or_email": username_or_email, "user_id": user.id},
            )

        return user

    async def create_access_token_for_user(self, user: User) -> str:
        """Create access token for user.

        Args:
            user (User): User instance

        Returns:
            str: JWT access token
        """
        access_token_expires = timedelta(minutes=self.settings.security.access_token_expire_minutes)
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
        )
        return access_token

    async def login(self, username_or_email: str, password: str) -> tuple[str, User]:
        """Login user and create session.

        Authenticates user, creates access token, and stores session.

        Args:
            username_or_email (str): User email or username
            password (str): Plain text password

        Returns:
            tuple[str, User]: Access token and user instance

        Raises:
            AuthenticationException: If authentication fails
        """
        # Authenticate user
        user = await self.authenticate_user(username_or_email, password)

        # Create access token
        access_token = await self.create_access_token_for_user(user)

        # Calculate expiration time
        access_token_expires = timedelta(minutes=self.settings.security.access_token_expire_minutes)
        expires_at = datetime.now(UTC) + access_token_expires

        # Create session (repository.create() commits internally)
        session_data = SessionCreate(
            user_id=user.id,
            token=access_token,
            expires_at=expires_at,
        )
        session = await self.session_repo.create(session_data)

        return access_token, user

    async def logout(self, token: str) -> None:
        """Logout user by deactivating session.

        Args:
            token (str): Access token to deactivate

        Raises:
            AuthenticationException: If session not found
        """
        # Get session
        session = await self.session_repo.get_by_token(token)
        if not session:
            raise AuthenticationException(
                message="Invalid session",
                details={"token": "not_found"},
            )

        # Deactivate session
        await self.session_repo.deactivate_session(token)
        await self.commit()

    async def get_user_from_token(self, token: str) -> User:
        """Get user from access token.

        Validates token and returns associated user.

        Args:
            token (str): JWT access token

        Returns:
            User: User instance

        Raises:
            AuthenticationException: If token is invalid or session not found
        """
        from app.core.security import decode_access_token

        # Decode token
        payload = decode_access_token(token)
        if not payload:
            raise AuthenticationException(
                message="Invalid or expired token",
                details={"token": "invalid"},
            )

        user_id = payload  # already did payload.get("sub") in the inner function
        if not user_id:
            raise AuthenticationException(
                message="Invalid token payload",
                details={"token": "missing_subject"},
            )

        # Check if session exists and is active
        session = await self.session_repo.get_active_by_token(token)
        if not session:
            raise AuthenticationException(
                message="Session not found or expired",
                details={"token": "session_invalid"},
            )

        # Get user
        user = await self.user_repo.get(int(user_id))
        if not user:
            raise AuthenticationException(
                message="User not found",
                details={"user_id": user_id},
            )

        # Check if user is active
        if not user.is_active:
            raise AuthenticationException(
                message="User account is inactive",
                details={"user_id": user.id},
            )

        return user
