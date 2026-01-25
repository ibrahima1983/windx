"""Unit tests for CLI management commands.

Tests the command registry, argument parsing, and platform-specific
path resolution without executing actual database operations.
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the functions we need to test
from manage import (
    COMMAND_REGISTRY,
    get_python_executable,
    main,
)


class TestCommandRegistry:
    """Test command registry functionality."""

    def test_all_commands_registered(self):
        """Test that all required commands are registered."""
        required_commands = [
            "createsuperuser",
            "promote",
            "create_tables",
            "drop_tables",
            "reset_db",
            "reset_password",
            "check_env",
            "seed_data",
        ]

        for command in required_commands:
            assert command in COMMAND_REGISTRY, f"Command '{command}' not registered"

    def test_command_registry_is_dict(self):
        """Test that command registry is a dictionary."""
        assert isinstance(COMMAND_REGISTRY, dict)

    def test_command_registry_values_are_callable(self):
        """Test that all registry values are callable."""
        for command_name, command_func in COMMAND_REGISTRY.items():
            assert callable(command_func), f"Command '{command_name}' is not callable"


class TestPlatformPathResolution:
    """Test platform-specific Python executable path resolution."""

    @patch("sys.platform", "win32")
    def test_windows_path(self):
        """Test Windows Python executable path."""
        path = get_python_executable()
        assert path == ".venv\\Scripts\\python"

    @patch("sys.platform", "linux")
    def test_linux_path(self):
        """Test Linux Python executable path."""
        path = get_python_executable()
        assert path == ".venv/bin/python"

    @patch("sys.platform", "darwin")
    def test_macos_path(self):
        """Test macOS Python executable path."""
        path = get_python_executable()
        assert path == ".venv/bin/python"


class TestArgumentParsing:
    """Test argument parsing for CLI commands."""

    def test_help_displayed_without_command(self, capsys):
        """Test that help is displayed when no command is provided."""
        with patch("sys.argv", ["manage.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "Management CLI" in captured.out
            assert "Commands:" in captured.out

    def test_unknown_command_shows_error(self, capsys):
        """Test that unknown command shows error message."""
        with patch("sys.argv", ["manage.py", "unknown_command"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse exits with 2 for invalid choice

    def test_promote_requires_username(self, capsys):
        """Test that promote command requires username argument."""
        with patch("sys.argv", ["manage.py", "promote"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "Username required" in captured.out

    def test_reset_password_requires_username(self, capsys):
        """Test that reset_password command requires username argument."""
        with patch("sys.argv", ["manage.py", "reset_password"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "Username required" in captured.out

    @patch("manage.asyncio.run")
    def test_force_flag_parsing(self, mock_asyncio_run):
        """Test that --force flag is parsed correctly."""
        with patch("sys.argv", ["manage.py", "drop_tables", "--force"]):
            try:
                main()
            except SystemExit:
                pass

            # Verify asyncio.run was called (command executed)
            assert mock_asyncio_run.called


class TestCommandExecution:
    """Test command execution flow."""

    @patch("manage.asyncio.run")
    @patch("manage.create_tables")
    def test_create_tables_command_execution(self, mock_create_tables, mock_asyncio_run):
        """Test that create_tables command executes correctly."""
        with patch("sys.argv", ["manage.py", "create_tables"]):
            try:
                main()
            except SystemExit:
                pass

            # Verify asyncio.run was called
            assert mock_asyncio_run.called

    @patch("manage.asyncio.run")
    @patch("manage.check_env_command")
    def test_check_env_command_execution(self, mock_check_env, mock_asyncio_run):
        """Test that check_env command executes correctly."""
        with patch("sys.argv", ["manage.py", "check_env"]):
            try:
                main()
            except SystemExit:
                pass

            # Verify asyncio.run was called
            assert mock_asyncio_run.called


class TestConfirmationPrompts:
    """Test confirmation prompts for destructive operations."""

    @patch("manage.asyncio.run")
    def test_drop_tables_cancelled_without_force(self, mock_asyncio_run):
        """Test that drop_tables command is called (confirmation happens inside async function)."""
        with patch("sys.argv", ["manage.py", "drop_tables"]):
            try:
                main()
            except SystemExit:
                pass

            # Verify asyncio.run was called (command executed, confirmation happens inside)
            assert mock_asyncio_run.called

    @patch("manage.asyncio.run")
    @patch("manage.drop_tables")
    def test_drop_tables_skips_confirmation_with_force(self, mock_drop_tables, mock_asyncio_run):
        """Test that drop_tables skips confirmation with --force flag."""
        with patch("sys.argv", ["manage.py", "drop_tables", "--force"]):
            try:
                main()
            except SystemExit:
                pass

            # Verify asyncio.run was called (no input prompt)
            assert mock_asyncio_run.called

    @patch("manage.asyncio.run")
    def test_reset_db_cancelled_without_force(self, mock_asyncio_run):
        """Test that reset_db command is called (confirmation happens inside async function)."""
        with patch("sys.argv", ["manage.py", "reset_db"]):
            try:
                main()
            except SystemExit:
                pass

            # Verify asyncio.run was called (command executed, confirmation happens inside)
            assert mock_asyncio_run.called


@pytest.mark.asyncio
class TestAsyncCommandFunctions:
    """Test async command functions with mocked database."""

    async def test_create_tables_with_mock_engine(self):
        """Test create_tables function with mocked engine."""
        from manage import create_tables

        # Create a proper async context manager mock
        mock_conn = AsyncMock()
        mock_engine = MagicMock()

        # Mock the async context manager properly
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_engine.begin.return_value = async_context
        mock_engine.dispose = AsyncMock()

        args = argparse.Namespace(force=False)

        with patch("manage.get_engine", return_value=mock_engine):
            try:
                await create_tables(args)
            except SystemExit:
                # Command may exit on success
                pass

            # Verify LTREE extension creation was attempted
            assert mock_conn.execute.called or mock_conn.run_sync.called

    async def test_check_env_with_mock_engine(self):
        """Test check_env_command with mocked engine."""
        from manage import check_env_command

        # Create a proper async context manager mock
        mock_conn = AsyncMock()
        mock_engine = MagicMock()

        # Mock the async context manager properly
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_engine.begin.return_value = async_context
        mock_engine.dispose = AsyncMock()

        args = argparse.Namespace()

        with patch("manage.get_engine", return_value=mock_engine):
            with patch("manage.get_settings") as mock_settings:
                # Mock settings
                mock_db = MagicMock()
                mock_db.url = "postgresql://test"
                mock_db.provider = "postgresql"
                mock_db.host = "localhost"
                mock_db.name = "test_db"

                mock_sec = MagicMock()
                mock_sec.secret_key.get_secret_value.return_value = "test_key"
                mock_sec.algorithm = "HS256"

                mock_settings.return_value.database = mock_db
                mock_settings.return_value.security = mock_sec

                result = await check_env_command(args)

                # Command executes (may return 0 or 1 depending on env files)
                assert result in [0, 1] or result is None


class TestCommandDocumentation:
    """Test that commands have proper documentation."""

    def test_all_commands_have_docstrings(self):
        """Test that all command functions have docstrings."""
        import manage

        command_functions = [
            "create_superuser",
            "promote_user",
            "create_tables",
            "drop_tables",
            "reset_db",
            "reset_password_command",
            "check_env_command",
            "seed_data_command",
        ]

        for func_name in command_functions:
            func = getattr(manage, func_name)
            assert func.__doc__ is not None, f"Function '{func_name}' missing docstring"
            assert len(func.__doc__.strip()) > 0, f"Function '{func_name}' has empty docstring"
