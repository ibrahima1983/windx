"""
Database Trigger Installation Script

This script installs PostgreSQL triggers and functions for the Windx configurator system.
Run this after creating the database schema to enable automatic LTREE path maintenance,
depth calculation, and price history tracking.

Usage:
    python -m app.database.sql.install_triggers

Or from the project root:
    .venv/scripts/python -m app.database.sql.install_triggers
"""

import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker


async def install_triggers(session: AsyncSession) -> None:
    """Install all database triggers and functions."""

    # Get the directory containing SQL scripts
    sql_dir = Path(__file__).parent

    # Scripts to install in order
    scripts = [
        "01_ltree_path_maintenance.sql",
        "02_depth_calculation.sql",
        "03_price_history.sql",
    ]

    print("Installing database triggers and functions...")
    print("-" * 60)

    for script_name in scripts:
        script_path = sql_dir / script_name

        if not script_path.exists():
            print(f"❌ Script not found: {script_name}")
            continue

        try:
            # Read SQL script
            with open(script_path, encoding="utf-8") as f:
                sql = f.read()

            # Execute SQL
            await session.execute(text(sql))
            await session.commit()

            print(f"✅ Installed: {script_name}")

        except Exception as e:
            print(f"❌ Error installing {script_name}: {e}")
            await session.rollback()
            raise

    print("-" * 60)
    print("✅ All triggers and functions installed successfully!")


async def verify_installation(session: AsyncSession) -> None:
    """Verify that triggers and functions were installed correctly."""

    print("\nVerifying installation...")
    print("-" * 60)

    # Check for functions
    functions = [
        "update_attribute_node_ltree_path",
        "calculate_attribute_node_depth",
        "log_configuration_price_change",
    ]

    for func_name in functions:
        result = await session.execute(
            text("""
                SELECT proname, prosrc 
                FROM pg_proc 
                WHERE proname = :func_name
            """),
            {"func_name": func_name},
        )
        row = result.fetchone()

        if row:
            print(f"✅ Function exists: {func_name}")
        else:
            print(f"❌ Function missing: {func_name}")

    # Check for triggers
    triggers = [
        ("trigger_update_attribute_node_ltree_path", "attribute_nodes"),
        ("trigger_calculate_attribute_node_depth", "attribute_nodes"),
        ("trigger_log_configuration_price_change", "configurations"),
    ]

    for trigger_name, table_name in triggers:
        result = await session.execute(
            text("""
                SELECT tgname, tgenabled 
                FROM pg_trigger 
                WHERE tgname = :trigger_name 
                AND tgrelid = :table_name::regclass
            """),
            {"trigger_name": trigger_name, "table_name": table_name},
        )
        row = result.fetchone()

        if row:
            enabled = row[1] == "O"  # 'O' means enabled
            status = "enabled" if enabled else "disabled"
            print(f"✅ Trigger exists: {trigger_name} on {table_name} ({status})")
        else:
            print(f"❌ Trigger missing: {trigger_name} on {table_name}")

    print("-" * 60)
    print("✅ Verification complete!")


async def uninstall_triggers(session: AsyncSession) -> None:
    """Uninstall all database triggers and functions."""

    print("Uninstalling database triggers and functions...")
    print("-" * 60)

    # Drop triggers first
    triggers = [
        ("trigger_update_attribute_node_ltree_path", "attribute_nodes"),
        ("trigger_calculate_attribute_node_depth", "attribute_nodes"),
        ("trigger_log_configuration_price_change", "configurations"),
    ]

    for trigger_name, table_name in triggers:
        try:
            await session.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}"))
            print(f"✅ Dropped trigger: {trigger_name}")
        except Exception as e:
            print(f"❌ Error dropping trigger {trigger_name}: {e}")

    # Drop functions
    functions = [
        "update_attribute_node_ltree_path",
        "calculate_attribute_node_depth",
        "log_configuration_price_change",
    ]

    for func_name in functions:
        try:
            await session.execute(text(f"DROP FUNCTION IF EXISTS {func_name}() CASCADE"))
            print(f"✅ Dropped function: {func_name}")
        except Exception as e:
            print(f"❌ Error dropping function {func_name}: {e}")

    await session.commit()

    print("-" * 60)
    print("✅ All triggers and functions uninstalled!")


async def main():
    """Main entry point."""
    import sys

    # Parse command line arguments
    command = sys.argv[1] if len(sys.argv) > 1 else "install"

    async with async_session_maker() as session:
        if command == "install":
            await install_triggers(session)
            await verify_installation(session)
        elif command == "verify":
            await verify_installation(session)
        elif command == "uninstall":
            await uninstall_triggers(session)
        else:
            print(f"Unknown command: {command}")
            print("Usage: python -m app.database.sql.install_triggers [install|verify|uninstall]")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
