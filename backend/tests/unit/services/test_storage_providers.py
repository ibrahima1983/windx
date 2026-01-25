"""Unit tests for storage providers.

This module tests storage provider implementations including:
- LocalStorageProvider
- SupabaseStorageProvider
- Provider factory functions
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import FileStorageSettings
from app.services.storage.local_provider import LocalStorageProvider
from app.services.storage.service import _create_storage_provider


class TestLocalStorageProvider:
    """Test cases for LocalStorageProvider."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def local_settings(self, temp_dir):
        """Create local storage settings."""
        return FileStorageSettings(
            provider="local",
            local_dir=temp_dir,
            base_url="/static/uploads",
        )

    @pytest.fixture
    def local_provider(self, local_settings):
        """Create local storage provider."""
        return LocalStorageProvider(local_settings)

    def test_init_creates_directory(self, temp_dir):
        """Test that initialization creates storage directory."""
        storage_dir = Path(temp_dir) / "new_storage"
        settings = FileStorageSettings(
            provider="local",
            local_dir=str(storage_dir),
        )

        provider = LocalStorageProvider(settings)

        assert storage_dir.exists()
        assert provider.storage_dir == storage_dir

    async def test_upload_file_success(self, local_provider, temp_dir):
        """Test successful file upload."""
        file_content = b"test file content"
        filename = "test.txt"

        result = await local_provider.upload_file(file_content, filename)

        assert result.success is True
        assert result.filename.startswith("upload_")
        assert result.filename.endswith(".txt")
        assert result.url.startswith("/static/uploads/")
        assert result.size == len(file_content)

        # Verify file was actually written
        uploaded_file = Path(temp_dir) / result.filename
        assert uploaded_file.exists()
        assert uploaded_file.read_bytes() == file_content

    async def test_upload_file_with_content_type(self, local_provider):
        """Test file upload with content type (ignored for local storage)."""
        file_content = b"image data"
        filename = "image.jpg"

        result = await local_provider.upload_file(file_content, filename, content_type="image/jpeg")

        assert result.success is True
        assert result.filename.endswith(".jpg")

    async def test_upload_file_failure(self, local_provider):
        """Test file upload failure."""
        # Make storage directory read-only to cause failure
        local_provider.storage_dir.chmod(0o444)

        try:
            file_content = b"test content"
            result = await local_provider.upload_file(file_content, "test.txt")

            assert result.success is False
            assert "Failed to upload file" in result.error
        finally:
            # Restore permissions for cleanup
            local_provider.storage_dir.chmod(0o755)

    async def test_delete_file_success(self, local_provider):
        """Test successful file deletion."""
        # First upload a file
        file_content = b"test content"
        upload_result = await local_provider.upload_file(file_content, "test.txt")

        # Then delete it
        success = await local_provider.delete_file(upload_result.filename)

        assert success is True

        # Verify file is gone
        file_path = local_provider.storage_dir / upload_result.filename
        assert not file_path.exists()

    async def test_delete_file_not_found(self, local_provider):
        """Test deleting non-existent file."""
        success = await local_provider.delete_file("nonexistent.txt")
        assert success is False

    async def test_delete_file_failure(self, local_provider):
        """Test file deletion failure."""
        # Create a file and make it undeletable
        test_file = local_provider.storage_dir / "test.txt"
        test_file.write_text("test")
        test_file.chmod(0o000)

        try:
            success = await local_provider.delete_file("test.txt")
            assert success is False
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)
            test_file.unlink(missing_ok=True)

    async def test_get_file_url_exists(self, local_provider):
        """Test getting URL for existing file."""
        # Upload a file first
        file_content = b"test content"
        upload_result = await local_provider.upload_file(file_content, "test.txt")

        url = await local_provider.get_file_url(upload_result.filename)

        assert url == f"/static/uploads/{upload_result.filename}"

    async def test_get_file_url_not_found(self, local_provider):
        """Test getting URL for non-existent file."""
        url = await local_provider.get_file_url("nonexistent.txt")
        assert url is None

    async def test_file_exists_true(self, local_provider):
        """Test file exists check for existing file."""
        # Upload a file first
        file_content = b"test content"
        upload_result = await local_provider.upload_file(file_content, "test.txt")

        exists = await local_provider.file_exists(upload_result.filename)
        assert exists is True

    async def test_file_exists_false(self, local_provider):
        """Test file exists check for non-existent file."""
        exists = await local_provider.file_exists("nonexistent.txt")
        assert exists is False

    def test_get_provider_name(self, local_provider):
        """Test getting provider name."""
        assert local_provider.get_provider_name() == "local"


class TestSupabaseStorageProvider:
    """Test cases for SupabaseStorageProvider."""

    @pytest.fixture
    def supabase_settings(self):
        """Create Supabase storage settings."""
        return FileStorageSettings(
            provider="supabase",
            supabase_bucket="test-bucket",
        )

    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        mock_client = MagicMock()

        # Mock storage operations
        mock_storage = MagicMock()
        mock_bucket = MagicMock()

        mock_client.storage = mock_storage
        mock_storage.from_.return_value = mock_bucket
        mock_storage.list_buckets.return_value = [MagicMock(name="test-bucket")]

        return mock_client, mock_bucket

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    def test_init_success(self, mock_create_client, supabase_settings, mock_supabase_client):
        """Test successful SupabaseStorageProvider initialization."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        assert provider.settings == supabase_settings
        assert provider.bucket_name == "test-bucket"
        assert provider.client == mock_client
        mock_create_client.assert_called_once_with("https://test.supabase.co", "test-key")

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", False)
    def test_init_no_supabase(self, supabase_settings):
        """Test initialization without supabase-py installed."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        with pytest.raises(ImportError, match="supabase-py is required"):
            SupabaseStorageProvider(supabase_settings, "https://test.supabase.co", "test-key")

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    def test_init_missing_credentials(self, mock_create_client, supabase_settings):
        """Test initialization with missing credentials."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        with pytest.raises(ValueError, match="Supabase URL and service role key are required"):
            SupabaseStorageProvider(supabase_settings, "", "test-key")

        with pytest.raises(ValueError, match="Supabase URL and service role key are required"):
            SupabaseStorageProvider(supabase_settings, "https://test.supabase.co", "")

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_upload_file_success(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test successful file upload to Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock successful upload
        mock_bucket.upload.return_value = MagicMock(error=None)
        mock_bucket.get_public_url.return_value = (
            "https://test.supabase.co/storage/v1/object/public/test-bucket/file.jpg"
        )

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        file_content = b"test image data"
        result = await provider.upload_file(file_content, "test.jpg", "image/jpeg")

        assert result.success is True
        assert result.filename.startswith("profile_images/upload_")
        assert result.filename.endswith(".jpg")
        assert (
            result.url == "https://test.supabase.co/storage/v1/object/public/test-bucket/file.jpg"
        )
        assert result.size == len(file_content)

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_upload_file_failure(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test file upload failure to Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock upload failure
        mock_bucket.upload.return_value = MagicMock(error="Upload failed")

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        file_content = b"test data"
        result = await provider.upload_file(file_content, "test.jpg")

        assert result.success is False
        assert "Supabase upload error" in result.error

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_upload_file_exception(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test file upload with exception."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock exception during upload
        mock_bucket.upload.side_effect = Exception("Network error")

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        file_content = b"test data"
        result = await provider.upload_file(file_content, "test.jpg")

        assert result.success is False
        assert "Failed to upload to Supabase" in result.error

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_delete_file_success(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test successful file deletion from Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock successful deletion
        mock_bucket.remove.return_value = MagicMock(error=None)

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        success = await provider.delete_file("test.jpg")
        assert success is True

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_delete_file_failure(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test file deletion failure from Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock deletion failure
        mock_bucket.remove.return_value = MagicMock(error="File not found")

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        success = await provider.delete_file("test.jpg")
        assert success is False

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_get_file_url_exists(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test getting URL for existing file in Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock file exists and URL generation
        mock_bucket.list.return_value = [{"name": "test.jpg"}]
        mock_bucket.get_public_url.return_value = (
            "https://test.supabase.co/storage/v1/object/public/test-bucket/test.jpg"
        )

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        url = await provider.get_file_url("test.jpg")
        assert url == "https://test.supabase.co/storage/v1/object/public/test-bucket/test.jpg"

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_get_file_url_not_found(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test getting URL for non-existent file in Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock file doesn't exist
        mock_bucket.list.return_value = []

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        url = await provider.get_file_url("nonexistent.jpg")
        assert url is None

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_file_exists_true(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test file exists check for existing file in Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock file exists
        mock_bucket.list.return_value = [{"name": "test.jpg"}]

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        exists = await provider.file_exists("test.jpg")
        assert exists is True

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    async def test_file_exists_false(
        self, mock_create_client, supabase_settings, mock_supabase_client
    ):
        """Test file exists check for non-existent file in Supabase."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        # Mock file doesn't exist
        mock_bucket.list.return_value = []

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        exists = await provider.file_exists("nonexistent.jpg")
        assert exists is False

    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    def test_get_provider_name(self, mock_create_client, supabase_settings, mock_supabase_client):
        """Test getting provider name."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        mock_client, mock_bucket = mock_supabase_client
        mock_create_client.return_value = mock_client

        provider = SupabaseStorageProvider(
            supabase_settings, "https://test.supabase.co", "test-key"
        )

        assert provider.get_provider_name() == "supabase"


class TestProviderFactory:
    """Test cases for provider factory functions."""

    def test_create_local_provider(self):
        """Test creating local storage provider."""
        settings = FileStorageSettings(provider="local")

        provider = _create_storage_provider(settings)

        assert isinstance(provider, LocalStorageProvider)
        assert provider.get_provider_name() == "local"

    @patch("app.services.storage.service.get_settings")
    @patch("app.services.storage.supabase_provider.SUPABASE_AVAILABLE", True)
    @patch("app.services.storage.supabase_provider.create_client")
    def test_create_supabase_provider_success(self, mock_create_client, mock_get_settings):
        """Test creating Supabase storage provider successfully."""
        from app.services.storage.supabase_provider import SupabaseStorageProvider

        # Mock main settings
        mock_main_settings = MagicMock()
        mock_main_settings.supabase_url = "https://test.supabase.co"
        mock_main_settings.supabase_service_role_key = MagicMock()
        mock_main_settings.supabase_service_role_key.get_secret_value.return_value = "test-key"
        mock_get_settings.return_value = mock_main_settings

        # Mock Supabase client
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        settings = FileStorageSettings(provider="supabase")
        provider = _create_storage_provider(settings)

        assert isinstance(provider, SupabaseStorageProvider)
        assert provider.get_provider_name() == "supabase"

    @patch("app.services.storage.service.get_settings")
    def test_create_supabase_provider_missing_url(self, mock_get_settings):
        """Test creating Supabase provider with missing URL."""
        mock_main_settings = MagicMock()
        mock_main_settings.supabase_url = None
        mock_main_settings.supabase_service_role_key = "test-key"
        mock_get_settings.return_value = mock_main_settings

        settings = FileStorageSettings(provider="supabase")

        with pytest.raises(ValueError, match="SUPABASE_URL is required"):
            _create_storage_provider(settings)

    @patch("app.services.storage.service.get_settings")
    def test_create_supabase_provider_missing_key(self, mock_get_settings):
        """Test creating Supabase provider with missing service key."""
        mock_main_settings = MagicMock()
        mock_main_settings.supabase_url = "https://test.supabase.co"
        mock_main_settings.supabase_service_role_key = None
        mock_get_settings.return_value = mock_main_settings

        settings = FileStorageSettings(provider="supabase")

        with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY is required"):
            _create_storage_provider(settings)

    def test_create_unsupported_provider(self):
        """Test creating unsupported storage provider."""
        settings = FileStorageSettings(provider="azure")  # Not implemented yet

        with pytest.raises(ValueError, match="Unsupported storage provider: azure"):
            _create_storage_provider(settings)
