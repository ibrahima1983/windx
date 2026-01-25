"""Test Supabase database connection.

NOTE: This is a manual integration test for Supabase connection.
It is skipped in automated test runs to avoid external dependencies.
Run manually with: python tests/unit/test_supabase.py
"""

import asyncio
import os
import socket
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.database.connection import get_engine

# Get project root and change to it
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))


def check_dns_resolution(hostname: str) -> dict:
    """Check DNS resolution for a hostname."""
    try:
        # Try to resolve the hostname
        addr_info = socket.getaddrinfo(hostname, None)
        ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
        ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

        return {"success": True, "ipv4": ipv4_addresses, "ipv6": ipv6_addresses, "all": addr_info}
    except socket.gaierror as e:
        return {"success": False, "error": str(e)}


# @pytest.mark.skip(reason="Manual integration test - requires live Supabase connection")
async def test_connection():
    """Test Supabase connection."""
    settings = get_settings()

    print(f"Testing connection to: {settings.database.provider}")
    print(f"Host: {settings.database.host}")
    print(f"Database: {settings.database.name}")
    print(f"User: {settings.database.user}")
    print()

    # Check DNS resolution first
    print("Checking DNS resolution...")
    dns_result = check_dns_resolution(settings.database.host)
    if not dns_result["success"]:
        print(f"[FAIL] DNS resolution failed: {dns_result['error']}")
        print("\nPossible solutions:")
        print("1. Check your internet connection")
        print("2. Try using a different DNS server (e.g., 8.8.8.8)")
        print("3. Check if your firewall is blocking DNS queries")
        print("4. Verify the Supabase hostname is correct")
        return False

    print("[OK] DNS resolved successfully")
    if dns_result["ipv4"]:
        print(f"  IPv4 addresses: {', '.join(dns_result['ipv4'])}")
    if dns_result["ipv6"]:
        print(f"  IPv6 addresses: {', '.join(dns_result['ipv6'])}")
    print()

    try:
        engine = get_engine()

        async with engine.begin() as conn:
            # Test basic query
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("[OK] Connection successful!")
            print(f"  PostgreSQL version: {version[:50]}...")

            # Test another query
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"  Current database: {db_name}")

        await engine.dispose()
        return True

    except Exception as e:
        print("[FAIL] Connection failed!")
        print(f"  Error: {e}")
        print("\nPossible solutions:")
        print("1. Check if Supabase project is active")
        print("2. Verify database credentials in .env.test")
        print("3. Check if your IP is allowed in Supabase settings")
        print("4. Try using port 6543 (transaction pooler) instead of 5432")
        return False


# @pytest.mark.skip(reason="Manual integration test - requires live Supabase connection")
async def test_connection2():
    """Test different Supabase pooler connection formats."""

    # Use pooler hostnames (IPv4 compatible)
    pooler_hosts = [
        "aws-1-eu-west-3.pooler.supabase.com",  # Session pooler
        "aws-1-eu-west-3.pooler.supabase.com",  # Transaction pooler
    ]

    print("\n" + "=" * 70)
    print("Testing Supabase Pooler Connections (IPv4 Compatible)")
    print("=" * 70)

    for i, hostname in enumerate(pooler_hosts, 1):
        pooler_type = "Session Pooler" if i == 1 else "Transaction Pooler"
        port = 5432 if i == 1 else 6543

        print(f"\nTest {i}: {pooler_type}")
        print("-" * 70)

        # Check DNS first
        print(f"Checking DNS for {hostname}...")
        dns_result = check_dns_resolution(hostname)
        if not dns_result["success"]:
            print(f"[FAIL] DNS resolution failed: {dns_result['error']}")
            continue

        print("[OK] DNS resolved successfully")
        if dns_result["ipv4"]:
            print(f"  IPv4: {', '.join(dns_result['ipv4'][:2])}")  # Show first 2 IPs

        # Build connection URL
        url = f"postgresql+asyncpg://postgres.vglmnngcvcrdzvnaopde:DhsRZdcOMMxhrzwY@{hostname}:{port}/postgres"

        print(f"Connecting to port {port}...")
        try:
            # Add timeout and connection options
            connect_args = {
                "timeout": 10,
                "command_timeout": 10,
            }

            # Disable prepared statements for transaction pooler
            if i == 2:
                connect_args["statement_cache_size"] = 0

            engine = create_async_engine(
                url,
                echo=False,
                pool_pre_ping=True,
                connect_args=connect_args,
                execution_options={"prepared_statement_cache_size": 0} if i == 2 else {},
            )

            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
                print("[OK] Connection successful!")
                print(f"  PostgreSQL: {version[:60]}...")

                # Test a simple query
                result = await conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                print(f"  Database: {db_name}")

            await engine.dispose()
            print(f"[OK] {pooler_type} test passed!")
            return True

        except Exception as e:
            print(f"[FAIL] Failed: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("⚠ All pooler connection attempts failed")
    print("=" * 70)
    print("\nTroubleshooting steps:")
    print("1. Verify your Supabase project is active")
    print("2. Check database credentials in .env")
    print("3. Ensure your IP is whitelisted in Supabase settings")
    print("4. Verify the pooler region matches your project")
    print("5. Try connecting from Supabase dashboard first")
    return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SUPABASE CONNECTION TEST")
    print("=" * 70)

    success = asyncio.run(test_connection())
    success2 = asyncio.run(test_connection2())

    if not (success or success2):
        print("\n" + "=" * 70)
        print("[WARNING] CONNECTION FAILED - IPv6 RESOLUTION ISSUE")
        print("=" * 70)
        print("\nThis is a known issue with Supabase IPv6-only addresses on Windows.")
        print("\nQuick fixes:")
        print("1. Enable IPv6 on Windows:")
        print("   Enable-NetAdapterBinding -Name '*' -ComponentID ms_tcpip6")
        print("\n2. Use port 6543 (connection pooler) instead of 5432")
        print("\n3. Use local PostgreSQL for development")
        print("\nSee docs/SUPABASE_CONNECTION_ISSUE.md for detailed solutions.")
        print("=" * 70)

    exit(0 if (success or success2) else 1)
