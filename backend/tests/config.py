"""Test configuration module.

This module provides test-specific settings that override the main
application settings for testing purposes.

Public Classes:
    TestSettings: Test configuration settings

Features:
    - Loads from .env.test file
    - Uses PostgreSQL database (Supabase or local)
    - Supports LTREE and JSONB PostgreSQL types
    - Disables caching and rate limiting
    - Safe test credentials
"""

import concurrent.futures
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings

__all__ = ["TestSettings", "get_test_settings"]


class TestSettings(Settings):
    """Test-specific settings.

    Inherits from main Settings but overrides with test-specific values.
    Loads configuration from .env.test file.

    Attributes:
        All attributes from Settings plus test-specific overrides
    """

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        str_strip_whitespace=True,
        validate_default=True,
        validate_assignment=True,
        use_attribute_docstrings=True,
        extra="ignore",
    )

    # Override debug to always be True in tests
    debug: bool = Field(default=True, description="Debug mode (always True in tests)")

    @model_validator(mode="after")
    def override_database_schema(self):
        """Override database schema to test_windx for test isolation."""
        # Force test schema to be test_windx
        self.database.schema_ = "test_windx"
        return self

    # Override database settings for testing
    # Now uses PostgreSQL with asyncpg for LTREE and JSONB support
    database_provider: str = Field(
        default="postgresql",
        description="Database provider for tests",
    )

    # Disable caching in tests by default
    cache_enabled: bool = Field(
        default=False,
        description="Cache enabled (disabled in tests)",
    )

    # Disable rate limiting in tests by default
    limiter_enabled: bool = Field(
        default=False,
        description="Rate limiter enabled (disabled in tests)",
    )

    # Test user credentials
    test_admin_username: str = Field(
        default="test_admin",
        description="Test admin username",
    )
    test_admin_email: str = Field(
        default="test_admin@example.com",
        description="Test admin email",
    )
    test_admin_password: str = Field(
        default="AdminPassword123!",
        description="Test admin password",
    )
    test_user_username: str = Field(
        default="test_user",
        description="Test regular user username",
    )
    test_user_email: str = Field(
        default="test_user@example.com",
        description="Test regular user email",
    )
    test_user_password: str = Field(
        default="UserPassword123!",
        description="Test regular user password",
    )


@lru_cache
def get_test_settings() -> TestSettings:
    """Get cached test settings.

    Returns:
        TestSettings: Test settings instance (cached singleton)

    Example:
        ```python
        settings = get_test_settings()
        assert settings.debug is True
        ```
    """
    return TestSettings()


def get_test_database_url() -> str:
    """Get test database URL from settings.

    Returns:
        str: PostgreSQL connection string with asyncpg driver

    Note:
        Uses asyncpg driver for full PostgreSQL feature support including
        LTREE extension and JSONB types required by the Windx schema.
    """
    test_settings = get_test_settings()

    # Access database settings from the nested database object
    db = test_settings.database

    # Build PostgreSQL connection string with asyncpg driver
    # Note: password is a SecretStr, so we need to get its value
    password = db.password.get_secret_value() if db.password else ""

    return f"postgresql+asyncpg://{db.user}:{password}@{db.host}:{db.port}/{db.name}"


def check_redis_available(host: str = "localhost", port: int = 6379, timeout: float = 1.0) -> bool:
    """Check if Redis is available and accessible.

    Args:
        host: Redis host (default: localhost)
        port: Redis port (default: 6379)
        timeout: Connection timeout in seconds (default: 1.0)

    Returns:
        bool: True if Redis is available, False otherwise
    """
    try:
        import asyncio

        import redis.asyncio as redis

        async def _check():
            client = None
            try:
                client = redis.Redis(
                    host=host,
                    port=port,
                    socket_connect_timeout=timeout,
                    socket_timeout=timeout,
                )
                await client.ping()
                return True
            except Exception:
                return False
            finally:
                # Ensure connection is properly closed
                if client is not None:
                    try:
                        await client.aclose()
                    except Exception:
                        pass

        # Run async check
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new one
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _check())
                return future.result(timeout=timeout + 1)
        else:
            return loop.run_until_complete(_check())
    except Exception:
        return False
