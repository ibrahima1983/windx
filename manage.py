"""Management CLI for the application.

Usage:
    python manage.py <command> [options]

Commands:
    createsuperuser              Create a new superuser account
    promote <username>           Promote an existing user to superuser
    create_tables                Create all database tables with LTREE extension
    drop_tables                  Drop all database tables (requires confirmation)
    reset_db                     Drop and recreate all tables (requires confirmation)
    reset_password <username>    Reset password for a user
    check_env                    Validate environment configuration
    seed_data                    Create sample data for development
    clean_db                     Clean orphaned types and recreate database
    verify_setup                 Verify complete setup is working
    stamp_alembic                Stamp Alembic to current version
    create_factory_mfg           Create factory-generated manufacturing data (configurable)
    delete_factory_mfg           Delete factory-generated manufacturing data
    create_factory_customers     Create factory-generated customer data
    delete_factory_customers     Delete factory-generated customer data
    check_db                     Check database connection and schema
    tables                       Display table information with pandas
    start                        Start the server (auto-detects gunicorn/uvicorn)
    stop                         Stop a running server by port
    curl                         Check server status, view logs, or make HTTP requests
    clean                        Stop all servers and clean up project directory
    openapi                      Generate OpenAPI schema JSON file from running server
    setup_fresh_db               Complete fresh database setup (drop, migrate, seed, verify)
                                 Use --no-sample-data to skip profile data seeding

Examples:
    python manage.py createsuperuser
    python manage.py promote john_doe
    python manage.py create_tables
    python manage.py drop_tables --force
    python manage.py reset_db
    python manage.py reset_password admin
    python manage.py check_env
    python manage.py seed_data
    python manage.py clean_db
    python manage.py verify_setup
    python manage.py stamp_alembic
    python manage.py create_factory_mfg --depth 3 --leaves 4
    python manage.py delete_factory_mfg --force
    python manage.py create_factory_customers --count 20
    python manage.py delete_factory_customers --force
    python manage.py check_db
    python manage.py tables --schema public
    python manage.py start
    python manage.py start --use uvicorn
    python manage.py start --use gunicorn --host 0.0.0.0 --port 8080
    python manage.py stop
    python manage.py stop --port 8000
    python manage.py curl --poke
    python manage.py curl --port 8000 --poke
    python manage.py curl --url http://127.0.0.1:8000/api/v1/users
    python manage.py curl --lines 50
    python manage.py clean
    python manage.py clean --force
    python manage.py openapi
    python manage.py openapi --host 0.0.0.0 --port 8080
    python manage.py openapi --output api_schema.json
    python manage.py setup_fresh_db
    python manage.py setup_fresh_db --force
    python manage.py setup_fresh_db --no-sample-data
"""

import argparse
import asyncio
import sys
from collections.abc import Callable
from pathlib import Path

# Add backend directory to sys.path to allow importing 'app'
sys.path.append(str(Path(__file__).parent / "backend"))

# Fix Windows CMD encoding issues with emojis
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Rich imports for beautiful terminal output
from rich.console import Console
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.database.base import Base
from app.database.connection import get_engine
from app.models.user import User


def get_project_name(show_warning: bool = True) -> str:
    """Get the project name from APP_NAME in .env or fallback to directory name.

    Priority:
    1. APP_NAME from .env file (cleaned for directory use)
    2. Current working directory basename (with warning)

    Args:
        show_warning: Whether to show warning if APP_NAME not found

    Returns:
        str: Project name for platformdirs
    """
    import os

    from dotenv import load_dotenv

    # Try to load .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Get APP_NAME from environment
    app_name = os.getenv("APP_NAME")

    if app_name:
        # Clean up app name for use as directory name
        # Remove special characters, keep alphanumeric, spaces, and hyphens
        import re

        clean_name = re.sub(r"[^\w\s-]", "", app_name)
        clean_name = re.sub(r"[-\s]+", "-", clean_name).strip("-").lower()
        return clean_name
    else:
        # Fallback to directory name with warning
        dir_name = Path.cwd().name

        if show_warning:
            console.print(
                f"[yellow]⚠ Warning:[/yellow] APP_NAME not found in .env, using directory name: [cyan]{dir_name}[/cyan]"
            )
            console.print(
                "[dim]This can lead to unexpected bugs if you run from different directories.[/dim]"
            )
            console.print("[dim]Recommendation: Set APP_NAME in your .env file.[/dim]")
            console.print()

        return dir_name.lower()


def get_project_dir() -> Path:
    """Get the project-specific directory for storing server data.

    Uses platformdirs to get the appropriate directory for the platform:
    - Windows: C:\\Users\\<user>\\AppData\\Local\\<project_name>
    - macOS: ~/Library/Application Support/<project_name>
    - Linux: ~/.local/share/<project_name>

    Returns:
        Path: Project directory path
    """
    from platformdirs import user_data_dir

    project_name = get_project_name()
    project_dir = Path(user_data_dir(project_name, appauthor=False))
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def get_server_slot_dir(port: int) -> Path:
    """Get the directory for a specific server slot (by port).

    Args:
        port: Server port number

    Returns:
        Path: Server slot directory path
    """
    slot_dir = get_project_dir() / str(port)
    slot_dir.mkdir(parents=True, exist_ok=True)
    return slot_dir


from rich import box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

# Initialize Rich console
console = Console()


async def create_superuser():
    """Create a new superuser account."""
    console.print(Panel.fit("[bold cyan]Create Superuser Account[/bold cyan]", border_style="cyan"))
    console.print()

    email = Prompt.ask("[cyan]Email[/cyan]").strip()
    username = Prompt.ask("[cyan]Username[/cyan]").strip()
    full_name = Prompt.ask("[cyan]Full name[/cyan] (optional)", default="").strip()
    password = Prompt.ask("[cyan]Password[/cyan]", password=True).strip()

    if not all([email, username, password]):
        console.print("\n[bold red]✗ Error:[/bold red] Email, username, and password are required!")
        sys.exit(1)

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Creating superuser...", total=None)

                # Check if user exists
                result = await session.execute(
                    select(User).where((User.email == email) | (User.username == username))
                )
                if result.scalar_one_or_none():
                    console.print("\n[bold red]✗ Error:[/bold red] User already exists!")
                    sys.exit(1)

                # Create superuser
                superuser = User(
                    email=email,
                    username=username,
                    full_name=full_name or username,
                    hashed_password=get_password_hash(password),
                    is_active=True,
                    is_superuser=True,
                )

                session.add(superuser)
                await session.commit()
                await session.refresh(superuser)

                progress.update(task, completed=True)

            # Success panel
            success_table = Table(show_header=False, box=box.SIMPLE)
            success_table.add_row("[cyan]Email:[/cyan]", f"[white]{superuser.email}[/white]")
            success_table.add_row("[cyan]Username:[/cyan]", f"[white]{superuser.username}[/white]")
            success_table.add_row(
                "[cyan]Full Name:[/cyan]", f"[white]{superuser.full_name}[/white]"
            )

            console.print()
            console.print(
                Panel(
                    success_table,
                    title="[bold green]✓ Superuser Created Successfully[/bold green]",
                    border_style="green",
                )
            )

        except Exception as e:
            await session.rollback()
            console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
            sys.exit(1)
        finally:
            await session.close()

    await engine.dispose()


async def promote_user(username: str):
    """Promote an existing user to superuser."""
    engine = get_engine()

    async with engine.begin() as conn:
        # First check if user exists and their current status
        check_result = await conn.execute(
            text("SELECT id, email, username, is_superuser FROM users WHERE username = :username"),
            {"username": username},
        )
        existing_user = check_result.fetchone()

        if not existing_user:
            print(f"❌ User '{username}' not found!")
            sys.exit(1)

        if existing_user.is_superuser:
            print(f"⚠️  User '{username}' is already a superuser!")
            print(f"   ID: {existing_user.id}")
            print(f"   Email: {existing_user.email}")
            return

        # Promote to superuser
        result = await conn.execute(
            text(
                "UPDATE users SET is_superuser = true "
                "WHERE username = :username "
                "RETURNING id, email, username, is_superuser"
            ),
            {"username": username},
        )
        user = result.fetchone()

        print(f"✅ User '{username}' promoted to superuser!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")

    await engine.dispose()


async def create_tables(args: argparse.Namespace):
    """Create all database tables with LTREE extension."""
    print("=== Creating Database Tables ===\n")

    engine = get_engine()

    try:
        async with engine.begin() as conn:
            # Create LTREE extension
            print("Creating LTREE extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
            print("✅ LTREE extension created")

            # Create all tables
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ All tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


async def drop_tables(args: argparse.Namespace):
    """Drop all database tables."""
    schema = getattr(args, "schema", "public")
    print(f"=== Dropping Database Tables (Schema: {schema}) ===\n")

    # Confirmation prompt unless --force is specified
    if not args.force:
        print(f"⚠️  WARNING: This will delete ALL data in the '{schema}' schema!")
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("Operation cancelled.")
            return

    engine = get_engine()

    try:
        async with engine.begin() as conn:
            # If schema is not 'public', drop the entire schema
            if schema != "public":
                print(f"Dropping schema '{schema}' and all its tables...")
                await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
                print(f"Creating schema '{schema}'...")
                await conn.execute(text(f"CREATE SCHEMA {schema}"))
                print(f"✅ Schema '{schema}' dropped and recreated successfully")
            else:
                print("Dropping all tables in public schema...")
                await conn.run_sync(Base.metadata.drop_all)
                print("✅ All tables dropped successfully")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


async def reset_db(args: argparse.Namespace):
    """Drop and recreate all database tables."""
    print("=== Resetting Database ===\n")

    # Confirmation prompt unless --force is specified
    if not args.force:
        print("⚠️  WARNING: This will delete ALL data and recreate the database!")
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("Operation cancelled.")
            return

    engine = get_engine()

    try:
        async with engine.begin() as conn:
            # Drop all tables
            print("Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ All tables dropped")

            # Create LTREE extension
            print("Creating LTREE extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
            print("✅ LTREE extension created")

            # Create all tables
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ All tables created successfully")

        print("\n✅ Database reset complete!")
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


async def reset_password_command(args: argparse.Namespace):
    """Reset password for a user."""
    print("=== Reset User Password ===\n")

    username = args.username

    # Prompt for new password
    new_password = input("New password: ").strip()
    if not new_password:
        print("❌ Error: Password cannot be empty!")
        sys.exit(1)

    confirm_password = input("Confirm password: ").strip()
    if new_password != confirm_password:
        print("❌ Error: Passwords do not match!")
        sys.exit(1)

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        try:
            # Find user
            result = await session.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()

            if not user:
                print(f"❌ Error: User '{username}' not found!")
                sys.exit(1)

            # Update password
            user.hashed_password = get_password_hash(new_password)
            await session.commit()

            print(f"✅ Password reset successfully for user '{username}'!")
            print(f"   Email: {user.email}")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error resetting password: {e}")
            sys.exit(1)
        finally:
            await session.close()

    await engine.dispose()


async def check_env_command(args: argparse.Namespace):
    """Validate environment configuration and database connectivity."""
    print("=== Environment Configuration Check ===\n")

    settings = get_settings()
    all_ok = True

    # Check required environment variables
    print("Checking environment variables...")

    required_vars = {
        "DATABASE_URL": settings.database.url,
        "SECRET_KEY": settings.security.secret_key.get_secret_value()
        if settings.security.secret_key
        else None,
        "ALGORITHM": settings.security.algorithm,
    }

    for var_name, var_value in required_vars.items():
        if var_value:
            print(f"✅ {var_name}: Set")
        else:
            print(f"❌ {var_name}: Missing")
            all_ok = False

    # Check database connectivity
    print("\nChecking database connectivity...")
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        print(f"   Provider: {settings.database.provider}")
        print(f"   Host: {settings.database.host}")
        print(f"   Database: {settings.database.name}")
        await engine.dispose()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        all_ok = False

    # Check environment files consistency
    print("\nChecking environment files...")
    project_root = Path(__file__).parent

    env_files = {
        ".env.example": project_root / ".env.example",
        ".env.test": project_root / ".env.test",
    }

    # Check for production env file
    prod_patterns = [".env.production", ".env.example.production", ".env.prod"]
    prod_file = None
    for pattern in prod_patterns:
        path = project_root / pattern
        if path.exists():
            prod_file = (pattern, path)
            break

    if prod_file:
        env_files[prod_file[0]] = prod_file[1]

    for name, path in env_files.items():
        if path.exists():
            print(f"✅ {name}: Found")
        else:
            print(f"⚠️  {name}: Not found")

    # Final result
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ All checks passed!")
        return 0
    else:
        print("❌ Some checks failed!")
        return 1


async def seed_data_command(args: argparse.Namespace):
    """Create sample data for development."""
    print("=== Seeding Sample Data ===\n")

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        try:
            # Check if data already exists
            result = await session.execute(select(User).limit(1))
            if result.scalar_one_or_none():
                print("⚠️  Database already contains data.")
                response = input("Do you want to continue? (yes/no): ").strip().lower()
                if response != "yes":
                    print("Operation cancelled.")
                    return

            # Create sample users (skip if they already exist)
            print("Checking/creating sample users...")

            from tests.config import get_test_settings

            test_settings = get_test_settings()

            # Check if admin user exists
            admin_result = await session.execute(
                select(User).where(User.email == "admin@example.com")
            )
            admin_user = admin_result.scalar_one_or_none()

            if not admin_user:
                admin_user = User(
                    email="admin@example.com",
                    username="admin",
                    full_name="Admin User",
                    hashed_password=get_password_hash(test_settings.test_admin_password),
                    is_active=True,
                    is_superuser=True,
                )
                session.add(admin_user)
                print(
                    f"✅ Created admin user: admin@example.com / {test_settings.test_admin_password}"
                )
            else:
                print("✅ Admin user already exists: admin@example.com")

            # Check if regular user exists
            user_result = await session.execute(
                select(User).where(User.email == "user@example.com")
            )
            regular_user = user_result.scalar_one_or_none()

            if not regular_user:
                regular_user = User(
                    email="user@example.com",
                    username="user",
                    full_name="Regular User",
                    hashed_password=get_password_hash(test_settings.test_user_password),
                    is_active=True,
                    is_superuser=False,
                )
                session.add(regular_user)
                print(
                    f"✅ Created regular user: user@example.com / {test_settings.test_user_password}"
                )
            else:
                print("✅ Regular user already exists: user@example.com")

            await session.commit()

            # Check if we need to create entry system data
            from app.models.manufacturing_type import ManufacturingType

            result = await session.execute(select(ManufacturingType).limit(1))
            if not result.scalar_one_or_none():
                print("\n📝 Creating entry system data...")

                # Import and create factory manufacturing data
                from _manager_utils import create_factory_manufacturing_data

                factory_result = await create_factory_manufacturing_data(
                    session, depth=2, root_leaves=2
                )

                print("✅ Entry system data created:")
                print(f"   Manufacturing Type: {factory_result['manufacturing_type_name']}")
                print(f"   Total Nodes: {factory_result['total_nodes']}")
                print("   Entry pages are now ready to use!")
            else:
                print("\n✅ Entry system data already exists")

            print("\n✅ Sample data seeded successfully!")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding data: {e}")
            sys.exit(1)
        finally:
            await session.close()

    await engine.dispose()


def get_python_executable() -> str:
    """Get the correct Python executable path for the platform.

    Returns:
        str: Path to Python executable in virtual environment
    """
    if sys.platform == "win32":
        return ".venv\\Scripts\\python"
    else:
        return ".venv/bin/python"


def print_help():
    """Print help message."""
    print(__doc__)


async def clean_db_types_command(args: argparse.Namespace):
    """Clean orphaned PostgreSQL types and recreate database."""
    print("=== Cleaning Database Types ===\n")

    engine = get_engine()

    try:
        async with engine.begin() as conn:
            print("Step 1: Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ Tables dropped")

            print("\nStep 2: Dropping orphaned types...")
            # Get all custom types in public schema
            result = await conn.execute(
                text("""
                SELECT typname 
                FROM pg_type t
                JOIN pg_namespace n ON t.typnamespace = n.oid
                WHERE n.nspname = 'public' 
                AND t.typtype = 'c'
                AND typname IN (
                    'users', 'sessions', 'customers', 'manufacturing_types',
                    'attribute_nodes', 'configurations', 'configuration_selections',
                    'configuration_templates', 'template_selections',
                    'quotes', 'orders', 'order_items'
                )
            """)
            )

            types_to_drop = [row[0] for row in result]
            if types_to_drop:
                print(f"Found {len(types_to_drop)} orphaned types: {types_to_drop}")

                for type_name in types_to_drop:
                    try:
                        await conn.execute(text(f"DROP TYPE IF EXISTS {type_name} CASCADE"))
                        print(f"  ✅ Dropped type: {type_name}")
                    except Exception as e:
                        print(f"  ⚠️  Could not drop {type_name}: {e}")
            else:
                print("No orphaned types found")

            print("\nStep 3: Creating LTREE extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
            print("✅ LTREE extension created")

            print("\nStep 4: Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ All tables created")

        print("\n" + "=" * 50)
        print("✅ Database cleaned and recreated!")
        print("\nNext steps:")
        print("1. Stamp alembic to current version:")
        print("   python manage.py stamp_alembic")
        print("\n2. Seed initial data:")
        print("   python manage.py seed_data")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


async def setup_fresh_db_command(args: argparse.Namespace):
    """Complete fresh database setup - drops everything and recreates from scratch."""
    console.print(Panel.fit("[bold cyan]Fresh Database Setup[/bold cyan]", border_style="cyan"))
    console.print()

    # Confirmation prompt unless --force is specified
    if not args.force:
        console.print(
            "⚠️  [yellow]WARNING: This will completely drop and recreate the database![/yellow]"
        )
        console.print("This command will:")
        console.print("  • Drop all database tables")
        console.print("  • Run Alembic migrations to head")
        console.print("  • Create all tables with LTREE extension")
        console.print("  • Seed initial data")
        console.print("  • Create minimal entry system data")
        console.print("  • Setup profile hierarchy with comprehensive attribute structure")
        if not args.no_sample_data:
            console.print("  • Seed sample profile data")
        else:
            console.print("  • [yellow]Skip sample profile data (--no-sample-data)[/yellow]")
        console.print("  • Create entry pages (accessories & glazing)")
        console.print("  • Verify complete setup")
        console.print()

        if not Confirm.ask("[red]Continue with fresh database setup?[/red]", default=False):
            console.print("[dim]Setup cancelled[/dim]")
            return 0
        console.print()

    python_exe = get_python_executable()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Drop all tables
            task = progress.add_task("[red]Dropping all tables...", total=None)
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            progress.update(task, description="[green]✓ All tables dropped")

            # Step 2: Run Alembic to head
            progress.update(task, description="[cyan]Running Alembic migrations...")
            import subprocess

            result = subprocess.run(
                [python_exe, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print(f"\n[bold red]✗ Alembic migration failed:[/bold red]")
                console.print(result.stderr)
                return 1
            progress.update(task, description="[green]✓ Alembic migrations completed")

            # Step 3: Create tables with LTREE extension
            progress.update(task, description="[cyan]Creating tables with LTREE extension...")
            engine = get_engine()
            async with engine.begin() as conn:
                # Create LTREE extension
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
            await engine.dispose()
            progress.update(task, description="[green]✓ Tables created with LTREE extension")

            # Step 4: Seed initial data
            progress.update(task, description="[cyan]Seeding initial data...")
            # Create a new args object for seed_data
            seed_args = argparse.Namespace()
            seed_args.force = True  # Skip confirmation for seed_data
            await seed_data_command(seed_args)
            progress.update(task, description="[green]✓ Initial data seeded")

            # Step 5: Create minimal entry system data
            progress.update(task, description="[cyan]Creating minimal entry system data...")
            result = subprocess.run(
                [python_exe, "_entry_setup.py", "--create-minimal"], capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print(f"\n[bold red]✗ Entry setup failed:[/bold red]")
                console.print(result.stderr)
                return 1
            progress.update(task, description="[green]✓ Minimal entry system data created")

            # Step 6: Setup profile hierarchy (CRITICAL for profile page)
            progress.update(task, description="[cyan]Setting up profile hierarchy...")
            result = subprocess.run(
                [python_exe, "scripts/setup_profile_hierarchy.py"], capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print(f"\n[bold red]✗ Profile hierarchy setup failed:[/bold red]")
                console.print(result.stderr)
                console.print(
                    "[yellow]This is critical for the profile page to work correctly![/yellow]"
                )
                return 1
            progress.update(task, description="[green]✓ Profile hierarchy setup completed")

            # Step 7: Seed profile data (optional but recommended)
            if not args.no_sample_data:
                progress.update(task, description="[cyan]Seeding profile data...")
                result = subprocess.run(
                    [python_exe, "scripts/seed_profile_data.py"], capture_output=True, text=True
                )
                if result.returncode != 0:
                    console.print(f"\n[bold yellow]⚠ Profile data seeding failed:[/bold yellow]")
                    console.print(result.stderr)
                    console.print("[dim]Profile page will work but won't have sample data[/dim]")
                    progress.update(
                        task, description="[yellow]⚠ Profile data seeding failed (optional)"
                    )
                else:
                    progress.update(task, description="[green]✓ Profile data seeded")
            else:
                progress.update(task, description="[yellow]⚠ Profile data seeding skipped (--no-sample-data)")
                console.print("\n[yellow]ℹ Profile data seeding skipped due to --no-sample-data flag[/yellow]")

            # Step 8: Create entry pages
            progress.update(task, description="[cyan]Creating entry pages...")
            result = subprocess.run(
                [python_exe, "_create_entry_pages.py"], capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print(f"\n[bold red]✗ Entry pages creation failed:[/bold red]")
                console.print(result.stderr)
                return 1
            progress.update(task, description="[green]✓ Entry pages created")

            # Step 9: Verify setup
            progress.update(task, description="[cyan]Verifying setup...")
            verify_args = argparse.Namespace()
            verify_result = await verify_setup_command(verify_args)
            if verify_result != 0:
                progress.update(task, description="[yellow]⚠ Setup verification had warnings")
            else:
                progress.update(task, description="[green]✓ Setup verification passed")

            progress.update(task, completed=True)

        # Success summary
        console.print()
        
        # Build dynamic success message based on what was actually done
        success_message = (
            "[green]✅ Fresh Database Setup Complete![/green]\n\n"
            "[cyan]•[/cyan] Database tables created with LTREE extension\n"
            "[cyan]•[/cyan] Alembic migrations applied\n"
            "[cyan]•[/cyan] Initial users and data seeded\n"
            "[cyan]•[/cyan] Entry system configured\n"
            "[cyan]•[/cyan] Profile hierarchy with comprehensive attribute structure created\n"
        )
        
        if not args.no_sample_data:
            success_message += "[cyan]•[/cyan] Sample profile data seeded\n"
        else:
            success_message += "[yellow]•[/yellow] Sample profile data skipped (--no-sample-data)\n"
            
        success_message += (
            "[cyan]•[/cyan] Entry pages (profile, accessories, glazing) ready\n\n"
            "[dim]You can now start the server and use the application![/dim]\n"
            "[dim]Profile page: http://localhost:8000/api/v1/admin/entry/profile[/dim]\n"
            "[dim]Start with: python manage.py start[/dim]"
        )
        
        if args.no_sample_data:
            success_message += (
                "\n\n[yellow]Note:[/yellow] To add sample profile data later, run:\n"
                "[dim]python scripts/seed_profile_data.py[/dim]"
            )
        
        console.print(
            Panel(
                success_message,
                title="[bold green]Setup Complete[/bold green]",
                border_style="green",
            )
        )

        return 0

    except Exception as e:
        console.print(f"\n[bold red]✗ Error during fresh database setup:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        return 1


async def verify_setup_command(args: argparse.Namespace):
    """Verify complete setup is working."""
    print("=" * 60)
    print("WINDX APPLICATION SETUP VERIFICATION")
    print("=" * 60)

    # Import test settings for password display
    from tests.config import get_test_settings

    test_settings = get_test_settings()

    engine = get_engine()
    all_ok = True

    try:
        async with engine.begin() as conn:
            # 1. Check LTREE extension
            print("\n1. Checking LTREE extension...")
            result = await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'ltree'"))
            if result.scalar():
                print("   ✅ LTREE extension installed")
            else:
                print("   ❌ LTREE extension missing")
                all_ok = False

            # 2. Check all tables exist
            print("\n2. Checking database tables...")
            result = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
                )
            )
            tables = [row[0] for row in result]
            expected_tables = [
                "alembic_version",
                "attribute_nodes",
                "configuration_selections",
                "configuration_templates",
                "configurations",
                "customers",
                "manufacturing_types",
                "order_items",
                "orders",
                "quotes",
                "sessions",
                "template_selections",
                "users",
            ]

            missing = set(expected_tables) - set(tables)
            if missing:
                print(f"   ❌ Missing tables: {missing}")
                all_ok = False
            else:
                print(f"   ✅ All {len(expected_tables)} tables exist")

            # 3. Check admin user
            print("\n3. Checking admin user...")
            result = await conn.execute(
                text(
                    "SELECT username, email, is_superuser, is_active FROM users WHERE username = 'admin'"
                )
            )
            admin = result.fetchone()
            if admin:
                print("   ✅ Admin user found")
                print(f"      Username: {admin[0]}")
                print(f"      Email: {admin[1]}")
                print(f"      Superuser: {admin[2]}")
                print(f"      Active: {admin[3]}")

                if not admin[2]:
                    print("   ❌ Admin user is not a superuser!")
                    all_ok = False
                if not admin[3]:
                    print("   ❌ Admin user is not active!")
                    all_ok = False
            else:
                print("   ⚠️  Admin user not found (run: python manage.py seed_data)")

            # 4. Check Alembic version
            print("\n4. Checking Alembic migrations...")
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            if version:
                print(f"   ✅ Alembic version: {version}")
            else:
                print("   ⚠️  No Alembic version found (run: python manage.py stamp_alembic)")

            # 5. Check user count
            print("\n5. Checking user accounts...")
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"   ✅ Total users: {user_count}")

        # 6. Check profile system setup (critical for profile page)
        print("\n6. Checking profile system setup...")
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_maker() as session:
            from app.core.manufacturing_type_resolver import ManufacturingTypeResolver

            profile_status = await ManufacturingTypeResolver.verify_profile_setup(session)

            if profile_status["status"] == "ok":
                print("   ✅ Profile system properly configured")
                if profile_status["has_rich_structure"]:
                    print("   ✅ Rich profile structure available")
                else:
                    print("   ⚠️  Basic profile structure only")
            elif profile_status["status"] == "warning":
                print("   ⚠️  Profile system has warnings:")
                for warning in profile_status["warnings"]:
                    print(f"      • {warning}")
                all_ok = False
            else:
                print("   ❌ Profile system has errors:")
                for error in profile_status["errors"]:
                    print(f"      • {error}")
                all_ok = False

            if profile_status["manufacturing_type"]:
                mfg = profile_status["manufacturing_type"]
                print(f"   Manufacturing Type: {mfg['name']} (ID: {mfg['id']})")
                print(f"   Attribute Count: {profile_status['attribute_count']}")

                if "structure_details" in profile_status:
                    details = profile_status["structure_details"]
                    print(
                        f"   Structure: {details['sections']} sections, {details['field_types']} field types, score {details['rich_score']}"
                    )
            else:
                print("   ❌ No manufacturing type found for profile page")
                all_ok = False

        print("\n" + "=" * 60)
        if all_ok:
            print("✅ ALL CHECKS PASSED - SETUP COMPLETE!")
            print("=" * 60)
            print("\nYou can now:")
            print("1. Start the server:")
            print(f"   {get_python_executable()} -m uvicorn main:app --reload")
            print("\n2. Login to admin panel:")
            print("   http://127.0.0.1:8000/api/v1/admin/login")
            print("   Username: admin")
            print(f"   Password: {test_settings.test_admin_password}")
            print("\n3. View API docs:")
            print("   http://127.0.0.1:8000/docs")
            return 0
        else:
            print("⚠️  SOME CHECKS FAILED OR INCOMPLETE")
            print("=" * 60)
            print("\nPlease review the warnings above.")
            return 1

    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        await engine.dispose()


async def check_profile_command(args: argparse.Namespace):
    """Check profile system setup and provide recommendations."""
    console.print(Panel.fit("[bold cyan]Profile System Check[/bold cyan]", border_style="cyan"))
    console.print()

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_maker() as session:
            from app.core.manufacturing_type_resolver import ManufacturingTypeResolver

            profile_status = await ManufacturingTypeResolver.verify_profile_setup(session)

            # Status summary
            if profile_status["status"] == "ok":
                console.print("✅ [green]Profile system is properly configured[/green]")
            elif profile_status["status"] == "warning":
                console.print("⚠️  [yellow]Profile system has warnings[/yellow]")
            else:
                console.print("❌ [red]Profile system has errors[/red]")

            console.print()

            # Details table
            details_table = Table(show_header=False, box=box.SIMPLE)

            if profile_status["manufacturing_type"]:
                mfg = profile_status["manufacturing_type"]
                details_table.add_row(
                    "[cyan]Manufacturing Type:[/cyan]",
                    f"[yellow]{mfg['name']}[/yellow] (ID: {mfg['id']})",
                )
                details_table.add_row(
                    "[cyan]Base Category:[/cyan]", f"[yellow]{mfg['base_category']}[/yellow]"
                )
            else:
                details_table.add_row("[cyan]Manufacturing Type:[/cyan]", "[red]None found[/red]")

            details_table.add_row(
                "[cyan]Attribute Count:[/cyan]",
                f"[yellow]{profile_status['attribute_count']}[/yellow]",
            )

            if "structure_details" in profile_status:
                details = profile_status["structure_details"]
                details_table.add_row(
                    "[cyan]Logical Sections:[/cyan]", f"[yellow]{details['sections']}[/yellow]"
                )
                details_table.add_row(
                    "[cyan]Field Types:[/cyan]", f"[yellow]{details['field_types']}[/yellow]"
                )
                details_table.add_row(
                    "[cyan]UI Components:[/cyan]", f"[yellow]{details['ui_components']}[/yellow]"
                )
                details_table.add_row(
                    "[cyan]Rich Score:[/cyan]", f"[yellow]{details['rich_score']}[/yellow]"
                )

                if details["section_names"]:
                    details_table.add_row(
                        "[cyan]Sections:[/cyan]",
                        f"[dim]{', '.join(details['section_names'])}[/dim]",
                    )

            details_table.add_row(
                "[cyan]Rich Structure:[/cyan]",
                "[green]Yes[/green]"
                if profile_status["has_rich_structure"]
                else "[yellow]Basic[/yellow]",
            )

            console.print(details_table)
            console.print()

            # Warnings
            if profile_status["warnings"]:
                console.print("[bold yellow]Warnings:[/bold yellow]")
                for warning in profile_status["warnings"]:
                    console.print(f"  • {warning}")
                console.print()

            # Errors
            if profile_status["errors"]:
                console.print("[bold red]Errors:[/bold red]")
                for error in profile_status["errors"]:
                    console.print(f"  • {error}")
                console.print()

            # Recommendations
            console.print("[bold cyan]Recommendations:[/bold cyan]")
            if profile_status["status"] == "error":
                console.print("  • Run: [yellow]python scripts/setup_profile_hierarchy.py[/yellow]")
                console.print("  • Or run: [yellow]python manage.py setup_fresh_db[/yellow]")
            elif profile_status["status"] == "warning":
                if not profile_status["has_rich_structure"]:
                    console.print(
                        "  • Consider adding more attributes to create richer product configuration"
                    )
                    console.print(
                        "  • Run: [yellow]python scripts/setup_profile_hierarchy.py[/yellow] for a comprehensive example"
                    )
                    console.print("  • Or create custom attributes through the admin interface")
                console.print(
                    "  • Consider running: [yellow]python scripts/seed_profile_data.py[/yellow] for sample data"
                )
            else:
                console.print("  • Profile system is ready!")
                console.print(
                    "  • Visit: [yellow]http://localhost:8000/api/v1/admin/entry/profile[/yellow]"
                )
                if profile_status["has_rich_structure"]:
                    console.print(
                        "  • Your profile system has a rich structure - great for complex products!"
                    )
                else:
                    console.print(
                        "  • Consider adding more attributes for richer product configuration"
                    )

            return 0 if profile_status["status"] != "error" else 1

    except Exception as e:
        console.print(f"[bold red]Error checking profile system:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        await engine.dispose()


async def stamp_alembic_command(args: argparse.Namespace):
    """Stamp Alembic to current version without running migrations."""
    print("=== Stamping Alembic Version ===\n")

    import subprocess

    python_exe = get_python_executable()
    result = subprocess.run(
        [python_exe, "-m", "alembic", "stamp", "head"], capture_output=True, text=True
    )

    if result.returncode == 0:
        print("✅ Alembic stamped to head version")
        print(result.stdout)
    else:
        print("❌ Error stamping Alembic:")
        print(result.stderr)
        sys.exit(1)


async def create_factory_mfg_command(args: argparse.Namespace):
    """Create factory-generated manufacturing data with configurable parameters."""
    from _manager_utils import create_factory_manufacturing_data

    console.print(
        Panel.fit("[bold cyan]Create Factory Manufacturing Data[/bold cyan]", border_style="cyan")
    )
    console.print()

    depth = args.depth if hasattr(args, "depth") and args.depth else 3
    leaves = args.leaves if hasattr(args, "leaves") and args.leaves else 3

    # Configuration table
    config_table = Table(show_header=False, box=box.SIMPLE)
    config_table.add_row("[cyan]Max Depth:[/cyan]", f"[yellow]{depth}[/yellow] levels")
    config_table.add_row("[cyan]Root Categories:[/cyan]", f"[yellow]{leaves}[/yellow]")
    console.print(config_table)
    console.print()

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("[cyan]Generating factory data...", total=None)

            async with session_maker() as session:
                result = await create_factory_manufacturing_data(
                    session,
                    depth=depth,
                    root_leaves=leaves,
                )

            progress.update(task, description="[green]✓ Factory data created")

        # Summary table
        summary_table = Table(
            title="[bold green]✓ Manufacturing Data Created[/bold green]", box=box.ROUNDED
        )
        summary_table.add_column("Property", style="cyan", no_wrap=True)
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Manufacturing Type", result["manufacturing_type_name"])
        summary_table.add_row("ID", str(result["manufacturing_type_id"]))
        summary_table.add_row("Base Price", f"${result['base_price']:.2f}")
        summary_table.add_row("Base Weight", f"{result['base_weight']:.2f} kg")
        summary_table.add_row("Total Nodes", f"{result['total_nodes']:,}")
        summary_table.add_row("Max Depth", str(result["max_depth"]))
        summary_table.add_row("Root Categories", str(result["root_leaves"]))

        console.print()
        console.print(summary_table)

        # Nodes by depth
        depth_table = Table(title="[bold]Nodes by Depth[/bold]", box=box.SIMPLE)
        depth_table.add_column("Level", justify="center", style="cyan")
        depth_table.add_column("Count", justify="right", style="yellow")

        for depth_level, count in sorted(result["nodes_by_depth"].items()):
            depth_table.add_row(f"Level {depth_level}", str(count))

        console.print()
        console.print(depth_table)

        # Nodes by type
        type_table = Table(title="[bold]Nodes by Type[/bold]", box=box.SIMPLE)
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", justify="right", style="yellow")

        for node_type, count in result["nodes_by_type"].items():
            type_table.add_row(node_type.capitalize(), str(count))

        console.print()
        console.print(type_table)

        if result.get("deepest_path"):
            console.print()
            console.print(f"[dim]Deepest Path:[/dim] [cyan]{result['deepest_path']}[/cyan]")

        # Next steps
        console.print()
        console.print(
            Panel(
                "[cyan]•[/cyan] View in admin dashboard: [link]http://127.0.0.1:8000/api/v1/admin/dashboard[/link]\n"
                "[cyan]•[/cyan] Create configurations using this manufacturing type\n"
                "[cyan]•[/cyan] Delete with: [yellow]python manage.py delete_factory_mfg --force[/yellow]",
                title="[bold]Next Steps[/bold]",
                border_style="dim",
            )
        )

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


async def delete_factory_mfg_command(args: argparse.Namespace):
    """Delete factory-generated manufacturing data."""
    from _manager_utils import delete_factory_manufacturing_data

    console.print(
        Panel.fit("[bold red]Delete Factory Manufacturing Data[/bold red]", border_style="red")
    )
    console.print()

    # Confirm deletion unless --force is used
    if not args.force:
        console.print(
            "[yellow]⚠ Warning:[/yellow] This will delete all 'Factory %' manufacturing types and their nodes."
        )
        if not Confirm.ask("[red]Continue with deletion?[/red]", default=False):
            console.print("[dim]Deletion cancelled[/dim]")
            sys.exit(0)
        console.print()

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("[red]Deleting factory data...", total=None)

            async with session_maker() as session:
                result = await delete_factory_manufacturing_data(session)

            progress.update(task, description="[green]✓ Deletion complete")

        if result["deleted"]:
            # Deletion summary table
            summary_table = Table(
                title="[bold green]✓ Deletion Complete[/bold green]", box=box.ROUNDED
            )
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Count", justify="right", style="yellow")

            summary_table.add_row("Manufacturing Types", str(result["deleted_types"]))
            summary_table.add_row("Total Nodes", f"{result['deleted_nodes']:,}")

            console.print()
            console.print(summary_table)

            # Details table
            if result["types"]:
                console.print()
                details_table = Table(title="[bold]Deleted Types[/bold]", box=box.SIMPLE)
                details_table.add_column("Name", style="cyan")
                details_table.add_column("ID", justify="right", style="dim")
                details_table.add_column("Nodes", justify="right", style="yellow")

                for type_info in result["types"]:
                    details_table.add_row(
                        type_info["name"], str(type_info["id"]), str(type_info["nodes"])
                    )

                console.print(details_table)
        else:
            console.print(f"\n[dim]{result['message']}[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


async def create_factory_customers_command(args: argparse.Namespace):
    """Create factory-generated customer data."""
    from _manager_utils import create_factory_customers

    console.print(
        Panel.fit("[bold cyan]Create Factory Customer Data[/bold cyan]", border_style="cyan")
    )
    console.print()

    count = args.count if hasattr(args, "count") and args.count else 10

    console.print(f"[cyan]Number of Customers:[/cyan] [yellow]{count}[/yellow]")
    console.print()

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("[cyan]Generating customer data...", total=None)

            async with session_maker() as session:
                result = await create_factory_customers(session, count=count)

            progress.update(task, description="[green]✓ Customer data created")

        # Summary table
        summary_table = Table(
            title="[bold green]✓ Customer Data Created[/bold green]", box=box.ROUNDED
        )
        summary_table.add_column("Customer Type", style="cyan")
        summary_table.add_column("Count", justify="right", style="yellow")

        for customer_type, type_count in result["customers_by_type"].items():
            summary_table.add_row(customer_type.capitalize(), str(type_count))

        summary_table.add_row("[bold]Total[/bold]", f"[bold]{result['total_customers']}[/bold]")

        console.print()
        console.print(summary_table)

        # Sample emails
        if result["sample_emails"]:
            console.print()
            email_table = Table(
                title="[bold]Sample Emails[/bold]", box=box.SIMPLE, show_header=False
            )
            email_table.add_column("Email", style="cyan")

            for email in result["sample_emails"]:
                email_table.add_row(email)

            console.print(email_table)

        # Next steps
        console.print()
        console.print(
            Panel(
                "[cyan]•[/cyan] View customers in admin panel\n"
                "[cyan]•[/cyan] Create configurations for these customers\n"
                "[cyan]•[/cyan] Delete with: [yellow]python manage.py delete_factory_customers --force[/yellow]",
                title="[bold]Next Steps[/bold]",
                border_style="dim",
            )
        )

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


async def delete_factory_customers_command(args: argparse.Namespace):
    """Delete factory-generated customer data."""
    from _manager_utils import delete_factory_customers

    console.print(
        Panel.fit("[bold red]Delete Factory Customer Data[/bold red]", border_style="red")
    )
    console.print()

    # Confirm deletion unless --force is used
    if not args.force:
        console.print(
            "[yellow]⚠ Warning:[/yellow] This will delete all factory-generated customers."
        )
        if not Confirm.ask("[red]Continue with deletion?[/red]", default=False):
            console.print("[dim]Deletion cancelled[/dim]")
            sys.exit(0)
        console.print()

    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("[red]Deleting customer data...", total=None)

            async with session_maker() as session:
                result = await delete_factory_customers(session)

            progress.update(task, description="[green]✓ Deletion complete")

        if result["deleted"]:
            # Deletion summary table
            summary_table = Table(
                title="[bold green]✓ Deletion Complete[/bold green]", box=box.ROUNDED
            )
            summary_table.add_column("Customer Type", style="cyan")
            summary_table.add_column("Deleted", justify="right", style="yellow")

            for customer_type, count in result["deleted_by_type"].items():
                summary_table.add_row(customer_type.capitalize(), str(count))

            summary_table.add_row(
                "[bold]Total[/bold]", f"[bold]{result['deleted_customers']}[/bold]"
            )

            console.print()
            console.print(summary_table)
        else:
            console.print(f"\n[dim]{result['message']}[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


async def check_db_command(args: argparse.Namespace):
    """Check database connection and schema."""
    console.print(
        Panel.fit("[bold cyan]Database Connection Check[/bold cyan]", border_style="cyan")
    )
    console.print()

    engine = get_engine()

    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("[cyan]Connecting to database...", total=None)

            async with engine.begin() as conn:
                # Check connection
                await conn.execute(text("SELECT 1"))
                progress.update(task, description="[green]✓ Connected successfully")

                # Get database info
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()

                # Check LTREE extension
                result = await conn.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'ltree'")
                )
                ltree_installed = bool(result.scalar())

                # List tables
                result = await conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
                    )
                )
                tables = [row[0] for row in result]

                progress.update(task, completed=True)

        # Database info table
        info_table = Table(title="[bold]Database Information[/bold]", box=box.ROUNDED)
        info_table.add_column("Property", style="cyan", no_wrap=True)
        info_table.add_column("Value", style="white")

        info_table.add_row("Status", "[green]✓ Connected[/green]")
        info_table.add_row(
            "PostgreSQL Version", version[:50] + "..." if len(version) > 50 else version
        )
        info_table.add_row(
            "LTREE Extension",
            "[green]✓ Installed[/green]" if ltree_installed else "[red]✗ Not Installed[/red]",
        )
        info_table.add_row("Total Tables", str(len(tables)))

        console.print(info_table)
        console.print()

        # Row counts table
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("[cyan]Counting rows...", total=len(tables))

            counts_table = Table(title="[bold]Table Row Counts[/bold]", box=box.ROUNDED)
            counts_table.add_column("Table", style="cyan", no_wrap=True)
            counts_table.add_column("Rows", justify="right", style="yellow")

            async with engine.begin() as conn:
                for table in tables:
                    if table != "alembic_version":
                        result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        counts_table.add_row(table, f"{count:,}")
                    progress.advance(task)

        console.print(counts_table)

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


async def tables_command(args: argparse.Namespace):
    """Display first 5 rows from each table."""
    console.print(
        Panel.fit("[bold cyan]Database Tables - First 5 Rows[/bold cyan]", border_style="cyan")
    )
    console.print()

    schema = args.schema if hasattr(args, "schema") and args.schema else "public"
    engine = get_engine()

    try:
        # Collect all table data first
        table_data_list = []

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("[cyan]Loading table data...", total=None)

            async with engine.begin() as conn:
                # Get all tables
                result = await conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = :schema ORDER BY tablename"
                    ),
                    {"schema": schema},
                )
                tables = [row[0] for row in result]

                if not tables:
                    console.print(f"[yellow]No tables found in schema '{schema}'[/yellow]")
                    return

                progress.update(task, description=f"[cyan]Loading {len(tables)} tables...")

                # Fetch data from all tables
                for table_name in tables:
                    try:
                        # Get column names
                        col_result = await conn.execute(
                            text("""
                                SELECT column_name, data_type 
                                FROM information_schema.columns 
                                WHERE table_schema = :schema 
                                AND table_name = :table_name 
                                ORDER BY ordinal_position
                            """),
                            {"schema": schema, "table_name": table_name},
                        )
                        columns = [(row[0], row[1]) for row in col_result]

                        if not columns:
                            continue

                        # Get first 5 rows
                        data_result = await conn.execute(
                            text(f"SELECT * FROM {table_name} LIMIT 5")
                        )
                        rows = data_result.fetchall()

                        # Get row count
                        count_result = await conn.execute(
                            text(f"SELECT COUNT(*) FROM {table_name}")
                        )
                        total_rows = count_result.scalar()

                        # Store table data
                        table_data_list.append(
                            {
                                "name": table_name,
                                "columns": columns,
                                "rows": rows,
                                "total_rows": total_rows,
                            }
                        )

                    except Exception as e:
                        table_data_list.append({"name": table_name, "error": str(e)})

                progress.update(task, description="[green]✓ Data loaded")

        # Now display all tables
        console.print()
        console.print(
            f"[cyan]Displaying {len(table_data_list)} tables from schema '[bold]{schema}[/bold]'[/cyan]"
        )
        console.print()

        for table_data in table_data_list:
            if "error" in table_data:
                console.print(
                    f"[yellow]⚠ Could not read table '{table_data['name']}': {table_data['error']}[/yellow]"
                )
                console.print()
                continue

            # Create table
            table = Table(
                title=f"[bold]{table_data['name']}[/bold] ([dim]{table_data['total_rows']} total rows[/dim])",
                box=box.ROUNDED,
                show_lines=False,
            )

            # Add columns (limit to reasonable number for display)
            max_cols = 8
            display_columns = table_data["columns"][:max_cols]

            for col_name, col_type in display_columns:
                display_name = col_name if len(col_name) <= 20 else col_name[:17] + "..."
                table.add_column(display_name, style="cyan", overflow="fold")

            if len(table_data["columns"]) > max_cols:
                table.add_column(f"... +{len(table_data['columns']) - max_cols} more", style="dim")

            # Add rows
            if table_data["rows"]:
                for row in table_data["rows"]:
                    str_values = []
                    for i, val in enumerate(row[:max_cols]):
                        if val is None:
                            str_values.append("[dim]NULL[/dim]")
                        else:
                            str_val = str(val)
                            if len(str_val) > 50:
                                str_values.append(str_val[:47] + "...")
                            else:
                                str_values.append(str_val)

                    if len(table_data["columns"]) > max_cols:
                        str_values.append("[dim]...[/dim]")

                    table.add_row(*str_values)
            else:
                empty_row = ["[dim]No data[/dim]"] * len(display_columns)
                if len(table_data["columns"]) > max_cols:
                    empty_row.append("")
                table.add_row(*empty_row)

            console.print(table)
            console.print()

        console.print(f"[green]✓ Displayed first 5 rows from {len(table_data_list)} tables[/green]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


def start_server_command(args: argparse.Namespace):
    """Start the server in a separate process (non-blocking)."""
    import os
    import pickle
    import shutil
    import subprocess
    from datetime import datetime

    from dotenv import load_dotenv

    console.print(Panel.fit("[bold cyan]Starting Server[/bold cyan]", border_style="cyan"))
    console.print()

    # Load .env file if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        console.print("[dim]✓ Loaded configuration from .env[/dim]")

    # Priority: argv > .env > defaults
    # Get values with proper priority
    def get_config_value(arg_value, env_key, default_value, value_type=str):
        """Get configuration value with priority: argv > .env > default."""
        # 1. Check argv (highest priority)
        if arg_value is not None:
            return arg_value

        # 2. Check .env file
        env_value = os.getenv(env_key)
        if env_value is not None:
            try:
                if value_type == bool:
                    return env_value.lower() in ("true", "1", "yes", "on")
                elif value_type == int:
                    return int(env_value)
                else:
                    return str(env_value)
            except (ValueError, AttributeError):
                pass

        # 3. Use default
        return default_value

    # Determine which server to use
    use_server = get_config_value(args.use if hasattr(args, "use") else None, "SERVER_TYPE", None)

    host = get_config_value(args.host if hasattr(args, "host") else None, "HOST", "127.0.0.1")

    port = get_config_value(args.port if hasattr(args, "port") else None, "PORT", 8000, int)

    workers = get_config_value(
        args.workers if hasattr(args, "workers") else None, "WORKERS", None, int
    )

    # For reload, check if --no-reload was explicitly passed
    reload_from_args = args.reload if hasattr(args, "reload") else None
    if reload_from_args is not None:
        reload = reload_from_args
    else:
        reload = get_config_value(None, "RELOAD", True, bool)

    # Auto-detect if not specified
    if use_server is None:
        # Check if gunicorn is installed
        if shutil.which("gunicorn"):
            use_server = "gunicorn"
            console.print("[cyan]✓ Detected:[/cyan] [green]gunicorn[/green] (production-ready)")
        else:
            use_server = "uvicorn"
            console.print("[cyan]✓ Detected:[/cyan] [yellow]uvicorn[/yellow] (development)")
    else:
        # Validate forced choice
        if use_server == "gunicorn" and not shutil.which("gunicorn"):
            console.print("[bold red]✗ Error:[/bold red] gunicorn not installed!")
            console.print("[dim]Install with:[/dim] pip install gunicorn")
            sys.exit(1)
        console.print(f"[cyan]✓ Using:[/cyan] [yellow]{use_server}[/yellow] (forced)")

    console.print()

    # Build command
    python_exe = get_python_executable()

    if use_server == "gunicorn":
        # Gunicorn command
        cmd = [
            python_exe,
            "-m",
            "gunicorn",
            "main:app",
            "--bind",
            f"{host}:{port}",
            "--worker-class",
            "uvicorn.workers.UvicornWorker",
        ]

        if workers:
            cmd.extend(["--workers", str(workers)])
        else:
            # Default to 4 workers for gunicorn
            cmd.extend(["--workers", "4"])

        if reload:
            cmd.append("--reload")

        server_type = "Gunicorn (Production)"

    else:
        # Uvicorn command
        cmd = [
            python_exe,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]

        if reload:
            cmd.append("--reload")

        server_type = "Uvicorn (Development)"

    # Display configuration with source indicators
    def get_source_indicator(arg_val, env_key):
        """Get indicator showing where value came from."""
        if arg_val is not None:
            return "[yellow](argv)[/yellow]"
        elif os.getenv(env_key):
            return "[cyan](.env)[/cyan]"
        else:
            return "[dim](default)[/dim]"

    config_table = Table(show_header=False, box=box.SIMPLE)
    config_table.add_row("[cyan]Server:[/cyan]", f"[yellow]{server_type}[/yellow]")

    host_source = get_source_indicator(args.host if hasattr(args, "host") else None, "HOST")
    config_table.add_row("[cyan]Host:[/cyan]", f"[white]{host}[/white] {host_source}")

    port_source = get_source_indicator(args.port if hasattr(args, "port") else None, "PORT")
    config_table.add_row("[cyan]Port:[/cyan]", f"[white]{port}[/white] {port_source}")

    if use_server == "gunicorn":
        workers_source = get_source_indicator(
            args.workers if hasattr(args, "workers") else None, "WORKERS"
        )
        config_table.add_row(
            "[cyan]Workers:[/cyan]", f"[white]{workers or 4}[/white] {workers_source}"
        )

    reload_source = (
        "[yellow](argv)[/yellow]"
        if hasattr(args, "reload") and args.reload is not None
        else ("[cyan](.env)[/cyan]" if os.getenv("RELOAD") else "[dim](default)[/dim]")
    )
    config_table.add_row(
        "[cyan]Reload:[/cyan]", f"[white]{'Yes' if reload else 'No'}[/white] {reload_source}"
    )
    config_table.add_row("[cyan]Process:[/cyan]", "[green]Background (non-blocking)[/green]")

    console.print(config_table)
    console.print()

    # Start server in background
    try:
        # Get server slot directory
        slot_dir = get_server_slot_dir(port)
        log_file = slot_dir / "server.log"
        console.print(f"[dim]Server slot: {slot_dir}[/dim]")
        console.print(f"[dim]Logging to: {log_file}[/dim]")
        console.print("[cyan]Starting server in background...[/cyan]")

        # Open log file for writing
        log_handle = open(log_file, "a", buffering=1)  # Line buffered

        # Start process in background (detached) with output redirected to log file
        if sys.platform == "win32":
            # Windows: Use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdout=log_handle,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout (log file)
                stdin=subprocess.DEVNULL,
            )
        else:
            # Unix: Use nohup-like behavior
            process = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout (log file)
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent
            )

        # Give it a moment to start
        import time

        time.sleep(2)

        # Check if process is still running
        if process.poll() is None:
            # Store process info in pickle file
            import pickle
            from datetime import datetime

            process_info = {
                "pid": process.pid,
                "host": host,
                "port": port,
                "server_type": use_server,
                "workers": workers or (4 if use_server == "gunicorn" else 1),
                "started_at": datetime.now().isoformat(),
                "command": " ".join(cmd),
                "log_file": str(log_file),
            }

            pickle_file = slot_dir / "process.pkl"
            try:
                with open(pickle_file, "wb") as f:
                    pickle.dump(process_info, f)
                console.print("[dim]✓ Process info saved[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ Could not save process info: {e}[/yellow]")

            console.print()
            console.print(
                Panel(
                    f"[green]✓ Server started successfully![/green]\n\n"
                    f"[cyan]•[/cyan] Process ID: [yellow]{process.pid}[/yellow]\n"
                    f"[cyan]•[/cyan] API URL: [link]http://{host}:{port}[/link]\n"
                    f"[cyan]•[/cyan] API Docs: [link]http://{host}:{port}/docs[/link]\n"
                    f"[cyan]•[/cyan] Admin Panel: [link]http://{host}:{port}/api/v1/admin/login[/link]\n"
                    f"[cyan]•[/cyan] Log File: [yellow]{log_file.name}[/yellow]\n\n"
                    f"[dim]Server is running in the background.[/dim]\n"
                    f"[dim]To check: python manage.py curl --poke[/dim]\n"
                    f"[dim]To view logs: python manage.py curl --lines 50[/dim]\n"
                    f"[dim]To stop: kill {process.pid} (Unix) or taskkill /PID {process.pid} (Windows)[/dim]",
                    title="[bold green]Server Running[/bold green]",
                    border_style="green",
                )
            )
        else:
            # Process died immediately
            stdout, stderr = process.communicate()
            console.print("\n[bold red]✗ Server failed to start![/bold red]")
            if stderr:
                console.print(f"\n[red]Error:[/red]\n{stderr.decode()}")
            if stdout:
                console.print(f"\n[dim]Output:[/dim]\n{stdout.decode()}")
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]✗ Error starting server:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def stop_command(args: argparse.Namespace):
    """Stop a running server by port."""
    import os
    import pickle

    from dotenv import load_dotenv

    console.print(Panel.fit("[bold yellow]Stop Server[/bold yellow]", border_style="yellow"))
    console.print()

    # Load .env file if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Priority: argv > .env > defaults
    port = args.port if hasattr(args, "port") and args.port else None
    if port is None:
        port = int(os.getenv("PORT", 8000))

    # Get server slot
    slot_dir = get_server_slot_dir(port)
    pickle_file = slot_dir / "process.pkl"

    if not pickle_file.exists():
        console.print(f"[yellow]⚠ No server found on port {port}[/yellow]")
        console.print(f"[dim]Looking in: {slot_dir}[/dim]")
        console.print()

        # List available servers
        console.print("[cyan]Available servers:[/cyan]")
        project_dir = get_project_dir()
        if project_dir.exists():
            slots = [d for d in project_dir.iterdir() if d.is_dir() and d.name.isdigit()]
            if slots:
                for slot in sorted(slots):
                    pkl = slot / "process.pkl"
                    if pkl.exists():
                        try:
                            with open(pkl, "rb") as f:
                                info = pickle.load(f)
                            console.print(
                                f"  • Port {info['port']}: PID {info['pid']} ({info['server_type']})"
                            )
                        except Exception:
                            pass
            else:
                console.print("  [dim]No servers found[/dim]")

        sys.exit(1)

    # Load process info
    try:
        with open(pickle_file, "rb") as f:
            process_info = pickle.load(f)
    except Exception as e:
        console.print(f"[red]✗ Error loading process info: {e}[/red]")
        sys.exit(1)

    # Display server info
    console.print(f"[cyan]Stopping server on port {port}...[/cyan]")
    console.print(f"[dim]PID: {process_info['pid']}[/dim]")
    console.print()

    # Try to stop the process
    try:
        import psutil

        try:
            process = psutil.Process(process_info["pid"])

            if not process.is_running():
                console.print(f"[yellow]⚠ Process {process_info['pid']} is not running[/yellow]")

                # Ask to clean up slot directory
                should_clean = args.force or Confirm.ask(
                    "[yellow]Clean up server slot directory?[/yellow]", default=True
                )

                if should_clean:
                    import shutil
                    import time

                    max_retries = 5
                    retry_delay = 0.5

                    for attempt in range(max_retries):
                        try:
                            shutil.rmtree(slot_dir)
                            console.print("[green]✓ Cleaned up slot directory[/green]")
                            break
                        except PermissionError:
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                retry_delay *= 2
                            else:
                                console.print(
                                    "[yellow]⚠ Could not delete slot directory (files may be locked)[/yellow]"
                                )
                                console.print(f"[dim]You can manually delete: {slot_dir}[/dim]")
                        except Exception as e:
                            console.print(f"[yellow]⚠ Error cleaning up: {e}[/yellow]")
                            break

                return

            # Terminate gracefully
            console.print("[cyan]Sending termination signal...[/cyan]")
            process.terminate()

            # Wait for process to terminate (max 10 seconds)
            try:
                process.wait(timeout=10)
                console.print("[green]✓ Server stopped gracefully[/green]")
            except psutil.TimeoutExpired:
                # Force kill if it doesn't terminate
                console.print("[yellow]⚠ Process didn't stop, force killing...[/yellow]")
                process.kill()
                console.print("[green]✓ Server force stopped[/green]")

            # Clean up slot directory with retry for Windows file locking
            import shutil
            import time

            max_retries = 5
            retry_delay = 0.5  # seconds

            for attempt in range(max_retries):
                try:
                    shutil.rmtree(slot_dir)
                    console.print("[green]✓ Cleaned up slot directory[/green]")
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        # Windows file locking - wait and retry
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        console.print(
                            "[yellow]⚠ Could not delete slot directory (files may be locked)[/yellow]"
                        )
                        console.print(f"[dim]You can manually delete: {slot_dir}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]⚠ Error cleaning up: {e}[/yellow]")
                    break

        except psutil.NoSuchProcess:
            console.print(f"[yellow]⚠ Process {process_info['pid']} not found[/yellow]")

            # Clean up slot directory anyway
            import shutil
            import time

            max_retries = 5
            retry_delay = 0.5

            for attempt in range(max_retries):
                try:
                    shutil.rmtree(slot_dir)
                    console.print("[green]✓ Cleaned up slot directory[/green]")
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        console.print(
                            "[yellow]⚠ Could not delete slot directory (files may be locked)[/yellow]"
                        )
                        console.print(f"[dim]You can manually delete: {slot_dir}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]⚠ Error cleaning up: {e}[/yellow]")
                    break

    except ImportError:
        console.print("[red]✗ psutil not installed[/red]")
        console.print("[dim]Install with: pip install psutil[/dim]")
        console.print()
        console.print("[yellow]Attempting manual stop...[/yellow]")

        # Provide manual instructions
        if sys.platform == "win32":
            console.print(f"[dim]Run: taskkill /PID {process_info['pid']} /F[/dim]")
        else:
            console.print(f"[dim]Run: kill {process_info['pid']}[/dim]")

        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error stopping server: {e}[/red]")
        sys.exit(1)


def clean_command(args: argparse.Namespace):
    """Stop all running servers and clean up project directory."""
    import pickle
    import shutil

    console.print(Panel.fit("[bold red]Clean Server Data[/bold red]", border_style="red"))
    console.print()

    project_dir = get_project_dir()

    if not project_dir.exists():
        console.print("[dim]No server data found[/dim]")
        return

    console.print(f"[cyan]Project directory:[/cyan] {project_dir}")
    console.print()

    # Find all server slots
    slots = [d for d in project_dir.iterdir() if d.is_dir() and d.name.isdigit()]

    if not slots:
        console.print("[dim]No servers found[/dim]")

        # Ask to delete empty directory
        if not args.force:
            if not Confirm.ask("[yellow]Delete empty project directory?[/yellow]", default=True):
                console.print("[dim]Cleanup cancelled[/dim]")
                return

        try:
            shutil.rmtree(project_dir)
            console.print("[green]✓ Project directory deleted[/green]")
        except Exception as e:
            console.print(f"[red]✗ Error deleting directory: {e}[/red]")

        return

    # Display servers to be stopped
    console.print(f"[yellow]Found {len(slots)} server(s):[/yellow]")

    servers_table = Table(box=box.ROUNDED)
    servers_table.add_column("Port", style="cyan")
    servers_table.add_column("PID", style="yellow")
    servers_table.add_column("Server", style="white")
    servers_table.add_column("Status", style="white")

    servers_to_stop = []

    for slot in sorted(slots):
        pkl = slot / "process.pkl"
        if pkl.exists():
            try:
                with open(pkl, "rb") as f:
                    info = pickle.load(f)

                # Check if process is running
                status = "Unknown"
                is_running = False
                try:
                    import psutil

                    process = psutil.Process(info["pid"])
                    if process.is_running():
                        status = f"[green]Running[/green] ({process.status()})"
                        is_running = True
                    else:
                        status = "[red]Not Running[/red]"
                except psutil.NoSuchProcess:
                    status = "[red]Not Found[/red]"
                except ImportError:
                    status = "[dim]Unknown (psutil not installed)[/dim]"
                except Exception as e:
                    status = f"[red]Error: {e}[/red]"

                servers_table.add_row(
                    str(info["port"]), str(info["pid"]), info["server_type"], status
                )

                servers_to_stop.append({"slot": slot, "info": info, "is_running": is_running})

            except Exception as e:
                # Add row even if we can't load the pickle file
                servers_table.add_row(slot.name, "N/A", "N/A", f"[red]Error: {e}[/red]")
                servers_to_stop.append({"slot": slot, "info": None, "is_running": False})
        else:
            # Slot exists but no process.pkl - add to table anyway
            servers_table.add_row(slot.name, "N/A", "N/A", "[yellow]No process info[/yellow]")
            servers_to_stop.append({"slot": slot, "info": None, "is_running": False})

    console.print(servers_table)
    console.print()

    # Confirm cleanup
    if not args.force:
        if not Confirm.ask(
            "[red]Stop all servers and delete project directory?[/red]", default=False
        ):
            console.print("[dim]Cleanup cancelled[/dim]")
            return

    console.print()

    # Stop running processes
    stopped_count = 0
    failed_count = 0

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    ) as progress:
        task = progress.add_task("[cyan]Stopping servers...", total=len(servers_to_stop))

        for server in servers_to_stop:
            if server["is_running"] and server["info"]:
                try:
                    import psutil

                    try:
                        process = psutil.Process(server["info"]["pid"])

                        # Kill all child processes first (important for Windows)
                        try:
                            children = process.children(recursive=True)
                            for child in children:
                                try:
                                    child.terminate()
                                except psutil.NoSuchProcess:
                                    pass

                            # Wait for children to terminate
                            if children:
                                psutil.wait_procs(children, timeout=3)
                        except Exception:
                            pass  # Continue even if child cleanup fails

                        # Now terminate the main process
                        process.terminate()

                        # Wait for process to terminate (max 5 seconds)
                        try:
                            process.wait(timeout=5)
                            console.print(
                                f"[green]✓ Stopped server on port {server['info']['port']} (PID {server['info']['pid']})[/green]"
                            )
                            stopped_count += 1
                        except psutil.TimeoutExpired:
                            # Force kill if it doesn't terminate
                            process.kill()
                            console.print(
                                f"[yellow]⚠ Force killed server on port {server['info']['port']} (PID {server['info']['pid']})[/yellow]"
                            )
                            stopped_count += 1

                    except psutil.NoSuchProcess:
                        # Process already terminated
                        console.print(
                            f"[yellow]⚠ Server on port {server['info']['port']} (PID {server['info']['pid']}) already stopped[/yellow]"
                        )
                        stopped_count += 1

                except Exception as e:
                    console.print(
                        f"[red]✗ Failed to stop server on port {server['info']['port']}: {e}[/red]"
                    )
                    failed_count += 1

            progress.advance(task)

    console.print()

    # Give Windows time to release file handles
    import time

    if stopped_count > 0:
        console.print("[dim]Waiting for file handles to be released...[/dim]")
        time.sleep(2)  # Increased wait time for Windows

    # Delete project directory with retry for Windows file locking

    max_retries = 5
    retry_delay = 0.5

    console.print("[cyan]Cleaning up project directory...[/cyan]")

    for attempt in range(max_retries):
        try:
            shutil.rmtree(project_dir)
            console.print(f"[green]✓ Deleted project directory: {project_dir}[/green]")
            break
        except PermissionError as e:
            if attempt < max_retries - 1:
                # Windows file locking - wait and retry
                console.print(
                    f"[dim]Waiting for files to be released... (attempt {attempt + 1}/{max_retries})[/dim]"
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                console.print(
                    "[yellow]⚠ Could not delete project directory (files may be locked)[/yellow]"
                )
                console.print(f"[dim]You can manually delete: {project_dir}[/dim]")
                console.print(f"[dim]Error: {e}[/dim]")
        except Exception as e:
            console.print(f"[red]✗ Error deleting directory: {e}[/red]")
            break

    # Summary
    console.print()
    summary_table = Table(show_header=False, box=box.SIMPLE)
    summary_table.add_row("[cyan]Servers stopped:[/cyan]", f"[green]{stopped_count}[/green]")
    if failed_count > 0:
        summary_table.add_row("[cyan]Failed:[/cyan]", f"[red]{failed_count}[/red]")
    summary_table.add_row("[cyan]Slots cleaned:[/cyan]", f"[yellow]{len(slots)}[/yellow]")

    console.print(summary_table)
    console.print()
    console.print("[green]✓ Cleanup complete![/green]")


def curl_command(args: argparse.Namespace):
    """Check server status, view logs, or make HTTP requests."""
    import os
    import pickle

    import requests
    from dotenv import load_dotenv

    console.print(Panel.fit("[bold cyan]Server Status & Logs[/bold cyan]", border_style="cyan"))
    console.print()

    # Load .env file if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Priority: argv > .env > defaults
    def get_config_value(arg_value, env_key, default_value, value_type=str):
        """Get configuration value with priority: argv > .env > default."""
        if arg_value is not None:
            return arg_value

        env_value = os.getenv(env_key)
        if env_value is not None:
            try:
                if value_type == bool:
                    return env_value.lower() in ("true", "1", "yes", "on")
                elif value_type == int:
                    return int(env_value)
                else:
                    return str(env_value)
            except (ValueError, AttributeError):
                pass

        return default_value

    # Get configuration
    port = get_config_value(args.port if hasattr(args, "port") else None, "PORT", 8000, int)

    host = get_config_value(args.host if hasattr(args, "host") else None, "HOST", "127.0.0.1")

    lines = get_config_value(args.lines if hasattr(args, "lines") else None, "LOG_LINES", 50, int)

    # Check for server slot
    slot_dir = get_server_slot_dir(port)
    pickle_file = slot_dir / "process.pkl"

    if not pickle_file.exists():
        console.print(f"[yellow]⚠ No server info found for port {port}[/yellow]")
        console.print(f"[dim]Looking in: {slot_dir}[/dim]")
        console.print()
        console.print("[cyan]Available servers:[/cyan]")

        # List all server slots
        project_dir = get_project_dir()
        if project_dir.exists():
            slots = [d for d in project_dir.iterdir() if d.is_dir() and d.name.isdigit()]
            if slots:
                for slot in sorted(slots):
                    pkl = slot / "process.pkl"
                    if pkl.exists():
                        try:
                            with open(pkl, "rb") as f:
                                info = pickle.load(f)
                            console.print(
                                f"  • Port {info['port']}: PID {info['pid']} ({info['server_type']})"
                            )
                        except Exception:
                            pass
            else:
                console.print("  [dim]No servers found[/dim]")
        else:
            console.print("  [dim]No servers found[/dim]")

        sys.exit(1)

    # Load process info
    try:
        with open(pickle_file, "rb") as f:
            process_info = pickle.load(f)
    except Exception as e:
        console.print(f"[red]✗ Error loading process info: {e}[/red]")
        sys.exit(1)

    # Display process info
    info_table = Table(title="[bold]Server Information[/bold]", box=box.ROUNDED)
    info_table.add_column("Property", style="cyan", no_wrap=True)
    info_table.add_column("Value", style="white")

    info_table.add_row("Process ID", str(process_info["pid"]))
    info_table.add_row("Host", process_info["host"])
    info_table.add_row("Port", str(process_info["port"]))
    info_table.add_row("Server Type", process_info["server_type"])
    info_table.add_row("Workers", str(process_info.get("workers", "N/A")))
    info_table.add_row("Started At", process_info["started_at"])
    info_table.add_row("Log File", process_info.get("log_file", "N/A"))

    console.print(info_table)
    console.print()

    # Check if --poke flag is set (health check)
    if hasattr(args, "poke") and args.poke:
        console.print("[cyan]Checking server health...[/cyan]")

        # Check if process is running
        import psutil

        try:
            process = psutil.Process(process_info["pid"])
            if process.is_running():
                console.print(f"[green]✓ Process is running[/green] (Status: {process.status()})")
            else:
                console.print("[red]✗ Process is not running[/red]")
                sys.exit(1)
        except psutil.NoSuchProcess:
            console.print(f"[red]✗ Process {process_info['pid']} not found[/red]")
            sys.exit(1)
        except ImportError:
            console.print("[yellow]⚠ psutil not installed, skipping process check[/yellow]")
            console.print("[dim]Install with: pip install psutil[/dim]")

        # HTTP health check
        url = f"http://{process_info['host']}:{process_info['port']}/health"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                console.print(f"[green]✓ HTTP health check passed[/green] ({response.status_code})")

                # Display health data
                try:
                    health_data = response.json()
                    health_table = Table(show_header=False, box=box.SIMPLE)
                    health_table.add_row(
                        "[cyan]Status:[/cyan]", f"[green]{health_data.get('status', 'N/A')}[/green]"
                    )
                    health_table.add_row("[cyan]App:[/cyan]", health_data.get("app_name", "N/A"))
                    health_table.add_row("[cyan]Version:[/cyan]", health_data.get("version", "N/A"))
                    console.print(health_table)
                except Exception:
                    pass
            else:
                console.print(
                    f"[yellow]⚠ HTTP health check returned {response.status_code}[/yellow]"
                )
        except requests.exceptions.ConnectionError:
            console.print(f"[red]✗ Could not connect to {url}[/red]")
            sys.exit(1)
        except requests.exceptions.Timeout:
            console.print("[red]✗ Request timed out[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]✗ HTTP health check failed: {e}[/red]")
            sys.exit(1)

    # If URL is provided, make HTTP request (curl functionality)
    elif hasattr(args, "url") and args.url:
        url = args.url
        method = args.method if hasattr(args, "method") and args.method else "GET"

        console.print(f"[cyan]Making {method} request to {url}...[/cyan]")
        console.print()

        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, timeout=10)
            elif method == "PUT":
                response = requests.put(url, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, timeout=10)
            else:
                console.print(f"[red]✗ Unsupported method: {method}[/red]")
                sys.exit(1)

            # Display response
            console.print(f"[cyan]Status:[/cyan] [yellow]{response.status_code}[/yellow]")
            console.print("[cyan]Headers:[/cyan]")
            for key, value in response.headers.items():
                console.print(f"  {key}: {value}")
            console.print()
            console.print("[cyan]Body:[/cyan]")

            try:
                # Try to pretty-print JSON
                import json

                json_data = response.json()
                console.print(json.dumps(json_data, indent=2))
            except Exception:
                # Fall back to text
                console.print(response.text)

        except Exception as e:
            console.print(f"[red]✗ Request failed: {e}[/red]")
            sys.exit(1)

    # Default: Show logs (tail last X lines)
    else:
        # Get log file from slot directory
        log_file_path = slot_dir / "server.log"
        if "log_file" in process_info:
            # Use stored path if available
            log_file_path = Path(process_info["log_file"])

        if not log_file_path.exists():
            console.print(f"[yellow]⚠ Log file not found: {log_file_path}[/yellow]")
            console.print("[dim]The server may have been started without logging enabled.[/dim]")
            sys.exit(1)

        console.print(f"[cyan]Showing last {lines} lines from {log_file_path.name}...[/cyan]")
        console.print()

        try:
            # Read last N lines from log file
            with open(log_file_path, encoding="utf-8", errors="ignore") as f:
                # Read all lines and get last N
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

                if not last_lines:
                    console.print("[dim]Log file is empty[/dim]")
                else:
                    # Display logs with syntax highlighting
                    for line in last_lines:
                        line = line.rstrip()

                        # Color code based on log level
                        if "ERROR" in line or "CRITICAL" in line:
                            console.print(f"[red]{line}[/red]")
                        elif "WARNING" in line or "WARN" in line:
                            console.print(f"[yellow]{line}[/yellow]")
                        elif "INFO" in line:
                            console.print(f"[cyan]{line}[/cyan]")
                        elif "DEBUG" in line:
                            console.print(f"[dim]{line}[/dim]")
                        else:
                            console.print(line)

                    console.print()
                    console.print(
                        f"[dim]Showing {len(last_lines)} of {len(all_lines)} total lines[/dim]"
                    )

        except Exception as e:
            console.print(f"[red]✗ Error reading log file: {e}[/red]")
            sys.exit(1)


def openapi_command(args: argparse.Namespace):
    """Generate OpenAPI schema JSON file from running server.

    This command fetches the OpenAPI schema from a running server and saves it to a file.

    Configuration Priority: argv > .env > defaults

    Args:
        args: Command line arguments
            - host: Server host (default: 127.0.0.1)
            - port: Server port (default: 8000)
            - output: Output file path (default: openapi_schema.json)

    Examples:
        python manage.py openapi
        python manage.py openapi --host 0.0.0.0 --port 8080
        python manage.py openapi --output api_schema.json
    """
    import json
    import os

    from dotenv import load_dotenv

    console.print(Panel.fit("[bold cyan]Generate OpenAPI Schema[/bold cyan]", border_style="cyan"))
    console.print()

    # Load .env file if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Priority: argv > .env > defaults
    host = args.host if hasattr(args, "host") and args.host else None
    if host is None:
        host = os.getenv("HOST", "127.0.0.1")

    port = args.port if hasattr(args, "port") and args.port else None
    if port is None:
        port = int(os.getenv("PORT", 8000))

    output = args.output if hasattr(args, "output") and args.output else None
    if output is None:
        output = os.getenv("OPENAPI_OUTPUT", "openapi_schema.json")

    # Build URL
    url = f"http://{host}:{port}/openapi.json"

    console.print(f"[cyan]Fetching OpenAPI schema from:[/cyan] {url}")
    console.print(f"[cyan]Output file:[/cyan] {output}")
    console.print()

    try:
        import requests

        # Fetch OpenAPI schema
        console.print("[cyan]Fetching schema...[/cyan]")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse JSON
        schema = response.json()

        # Save to file
        console.print(f"[cyan]Writing to {output}...[/cyan]")
        with open(output, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

        # Get file size
        file_size = os.path.getsize(output)
        file_size_kb = file_size / 1024

        # Success message
        console.print()
        console.print(
            Panel(
                f"[green]✓ OpenAPI schema generated successfully![/green]\n\n"
                f"[cyan]File:[/cyan] {output}\n"
                f"[cyan]Size:[/cyan] {file_size_kb:.2f} KB\n"
                f"[cyan]Endpoints:[/cyan] {len(schema.get('paths', {}))}",
                border_style="green",
            )
        )

    except ImportError:
        console.print("[red]✗ Error: 'requests' library not installed[/red]")
        console.print("[dim]Install with: pip install requests[/dim]")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Error: Could not connect to server at {url}[/red]")
        console.print()
        console.print("[yellow]Make sure the server is running:[/yellow]")
        console.print(f"[dim]  python manage.py start --host {host} --port {port}[/dim]")
        console.print("[dim]  python manage.py curl --poke[/dim]")
        sys.exit(1)
    except requests.exceptions.Timeout:
        console.print("[red]✗ Error: Request timed out[/red]")
        console.print("[dim]Server may be slow to respond[/dim]")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]✗ HTTP Error: {e}[/red]")
        console.print(f"[dim]Status code: {response.status_code}[/dim]")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print("[red]✗ Error: Invalid JSON response from server[/red]")
        console.print("[dim]Server may not be returning valid OpenAPI schema[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


# Command registry mapping command names to functions
COMMAND_REGISTRY: dict[str, Callable[[argparse.Namespace], None]] = {
    "createsuperuser": lambda args: asyncio.run(create_superuser()),
    "promote": lambda args: asyncio.run(promote_user(args.username)),
    "create_tables": lambda args: asyncio.run(create_tables(args)),
    "drop_tables": lambda args: asyncio.run(drop_tables(args)),
    "reset_db": lambda args: asyncio.run(reset_db(args)),
    "reset_password": lambda args: asyncio.run(reset_password_command(args)),
    "check_env": lambda args: asyncio.run(check_env_command(args)),
    "seed_data": lambda args: asyncio.run(seed_data_command(args)),
    "clean_db": lambda args: asyncio.run(clean_db_types_command(args)),
    "verify_setup": lambda args: sys.exit(asyncio.run(verify_setup_command(args))),
    "stamp_alembic": lambda args: asyncio.run(stamp_alembic_command(args)),
    "create_factory_mfg": lambda args: asyncio.run(create_factory_mfg_command(args)),
    "delete_factory_mfg": lambda args: asyncio.run(delete_factory_mfg_command(args)),
    "create_factory_customers": lambda args: asyncio.run(create_factory_customers_command(args)),
    "delete_factory_customers": lambda args: asyncio.run(delete_factory_customers_command(args)),
    "check_db": lambda args: asyncio.run(check_db_command(args)),
    "tables": lambda args: asyncio.run(tables_command(args)),
    "start": lambda args: start_server_command(args),
    "stop": lambda args: stop_command(args),
    "curl": lambda args: curl_command(args),
    "clean": lambda args: clean_command(args),
    "openapi": lambda args: openapi_command(args),
    "setup_fresh_db": lambda args: sys.exit(asyncio.run(setup_fresh_db_command(args))),
    "check_profile": lambda args: sys.exit(asyncio.run(check_profile_command(args))),
}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Management CLI for the application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=list(COMMAND_REGISTRY.keys()),
        help="Command to execute",
    )

    parser.add_argument(
        "username",
        nargs="?",
        help="Username (for promote and reset_password commands)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts for destructive operations",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Maximum depth for factory manufacturing data (default: 3)",
    )

    parser.add_argument(
        "--leaves",
        type=int,
        default=3,
        help="Number of root categories for factory manufacturing data (default: 3)",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of items to create (for factory customers, default: 10)",
    )

    parser.add_argument(
        "--schema",
        type=str,
        default="public",
        help="Database schema name (for tables and drop_tables commands, default: public)",
    )

    # Server start arguments
    parser.add_argument(
        "--use",
        type=str,
        choices=["uvicorn", "gunicorn"],
        help="Force specific server (auto-detects if not specified)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
    )

    parser.add_argument(
        "--workers",
        type=int,
        help="Number of worker processes (gunicorn only, default: 4)",
    )

    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable auto-reload on code changes",
    )

    # Curl command arguments
    parser.add_argument(
        "--poke",
        action="store_true",
        help="Check if server is running and healthy (curl command)",
    )

    parser.add_argument(
        "--url",
        type=str,
        help="URL to make HTTP request to (curl command)",
    )

    parser.add_argument(
        "--method",
        type=str,
        choices=["GET", "POST", "PUT", "DELETE"],
        default="GET",
        help="HTTP method for curl request (default: GET)",
    )

    parser.add_argument(
        "--lines",
        type=int,
        help="Number of log lines to show (curl command, default: 50)",
    )

    # OpenAPI command arguments
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for OpenAPI schema (openapi command, default: openapi_schema.json)",
    )

    parser.add_argument(
        "--no-sample-data",
        action="store_true",
        help="Skip seeding sample profile data (setup_fresh_db command)",
    )

    args = parser.parse_args()

    # Show help if no command provided
    if not args.command:
        print_help()
        sys.exit(1)

    # Validate username for commands that require it
    if args.command in ["promote", "reset_password"] and not args.username:
        print(f"❌ Error: Username required for '{args.command}' command!")
        print(f"Usage: python manage.py {args.command} <username>")
        sys.exit(1)

    # Execute command
    try:
        COMMAND_REGISTRY[args.command](args)
    except KeyError:
        print(f"❌ Unknown command: {args.command}")
        print_help()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error executing command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
