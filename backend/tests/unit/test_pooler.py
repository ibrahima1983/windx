"""Test Supabase pooler connection.

NOTE: This is a manual integration test for Supabase connection.
It is skipped in automated test runs to avoid external dependencies.
Run manually with: python tests/unit/test_pooler.py
"""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.skip(reason="Manual integration test - requires live Supabase connection")
async def test_connection():
    """Test Supabase transaction pooler connection."""

    url = "postgresql+asyncpg://postgres.vglmnngcvcrdzvnaopde:DhsRZdcOMMxhrzwY@aws-1-eu-west-3.pooler.supabase.com:6543/postgres"

    print("Testing Supabase Transaction Pooler connection...")
    print("Host: aws-1-eu-west-3.pooler.supabase.com")
    print("Port: 6543")
    print("User: postgres.vglmnngcvcrdzvnaopde")
    print()

    try:
        engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=3,
        )

        async with engine.begin() as conn:
            # Test basic query
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✓ Connection successful!")
            print(f"  PostgreSQL version: {version[:80]}...")

            # Test another query
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"  Current database: {db_name}")

            # Test user
            result = await conn.execute(text("SELECT current_user"))
            user = result.scalar()
            print(f"  Current user: {user}")

        await engine.dispose()
        print("\n✓ All tests passed!")
        return True

    except Exception as e:
        print("\n✗ Connection failed!")
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
