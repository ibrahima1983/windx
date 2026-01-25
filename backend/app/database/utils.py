"""Database utilities and helper functions.

This module provides utility functions for database operations including
query helpers, transaction management, and common database patterns.

Public Functions:
    execute_raw_query: Execute raw SQL query
    check_connection: Check database connection health
    get_table_names: Get all table names in database
    enable_ltree_extension: Enable PostgreSQL LTREE extension

Features:
    - Raw SQL execution
    - Connection health checks
    - Database introspection
    - Transaction helpers
    - PostgreSQL extension management
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_engine

__all__ = [
    "execute_raw_query",
    "check_connection",
    "get_table_names",
    "enable_ltree_extension",
]


async def execute_raw_query(
    db: AsyncSession,
    query: str,
    params: dict | None = None,
) -> list[dict]:
    """Execute raw SQL query and return results.

    Args:
        db (AsyncSession): Database session
        query (str): SQL query string
        params (dict | None): Query parameters

    Returns:
        list[dict]: Query results as list of dictionaries

    Example:
        ```python
        results = await execute_raw_query(
            db,
            "SELECT * FROM users WHERE email = :email",
            {"email": "user@example.com"}
        )
        ```
    """
    result = await db.execute(text(query), params or {})
    return [dict(row._mapping) for row in result.fetchall()]


async def check_connection() -> bool:
    """Check database connection health.

    Returns:
        bool: True if connection is healthy, False otherwise

    Example:
        ```python
        if await check_connection():
            print("Database is healthy")
        ```
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_table_names() -> list[str]:
    """Get all table names in the database.

    Returns:
        list[str]: List of table names

    Example:
        ```python
        tables = await get_table_names()
        print(f"Tables: {tables}")
        ```
    """
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
        )
        return [row[0] for row in result.fetchall()]


async def enable_ltree_extension() -> bool:
    """Enable PostgreSQL LTREE extension.

    This function enables the LTREE extension which provides data types
    and functions for representing hierarchical tree-like structures.

    The LTREE extension is required for the Windx attribute hierarchy system.

    Returns:
        bool: True if extension was enabled successfully, False otherwise

    Raises:
        Exception: If extension cannot be enabled

    Example:
        ```python
        # Enable during application startup
        @app.on_event("startup")
        async def startup():
            await init_db()
            await enable_ltree_extension()
        ```

    Note:
        This function is idempotent - it can be called multiple times safely.
        The extension will only be created if it doesn't already exist.
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            # Enable LTREE extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))

            # Verify extension is installed
            result = await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'ltree'"))
            if not result.scalar():
                raise Exception("LTREE extension failed to install")

            print("[OK] LTREE extension enabled")
            return True
    except Exception as e:
        print(f"[ERROR] Failed to enable LTREE extension: {e}")
        raise


async def execute_sql_file(file_path: str | Path) -> None:
    """Execute SQL commands from a file.

    Args:
        file_path: Path to SQL file

    Raises:
        FileNotFoundError: If SQL file doesn't exist
        Exception: If SQL execution fails

    Example:
        ```python
        await execute_sql_file("app/database/sql/enable_ltree.sql")
        ```
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")

    sql_content = file_path.read_text()

    engine = get_engine()
    async with engine.begin() as conn:
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        for statement in statements:
            if statement:
                await conn.execute(text(statement))

    print(f"[OK] Executed SQL file: {file_path}")
