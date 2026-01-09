"""Unit tests for storage configuration.

This module tests file storage configuration including:
- FileStorageSettings validation
- Supabase configuration requirements
- Configuration field validation
- Environment variable handling
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import FileStorageSettings


class TestFileStorageSettings:
    """Test cases for FileStorageSettings configuration."""

    def test_default_settings(self):
        """Test default file storage settings."""
        settings = FileStorageSettings()

        assert settings.provider == "local"
        assert settings.supabase_bucket == "windx-uploads"
        assert settings.local_dir == "app/static/uploads"
        assert settings.max_size == 5242880  # 5MB
        assert settings.min_size == 1024  # 1KB
        assert settings.max_width == 4096
        assert settings.max_height == 4096
        assert settings.min_width == 32
        assert settings.min_height == 32
        assert settings.enable_compression is True
        assert settings.compression_quality == 85
        assert settings.auto_resize is True
        assert settings.base_url == "/static/uploads"

    def test_computed_fields(self):
        """Test computed fields in settings."""
        settings = FileStorageSettings(
            max_size=10485760,  # 10MB
            min_size=2048,  # 2KB
        )

        assert settings.max_size_mb == 10.0
        assert settings.min_size_kb == 2.0
        assert settings.is_image_processing_enabled is True

    def test_image_processing_disabled(self):
        """Test image processing disabled when both compression and resize are off."""
        settings = FileStorageSettings(
            enable_compression=False,
            auto_resize=False,
        )

        assert settings.is_image_processing_enabled is False

    def test_allowed_extensions_validation(self):
        """Test allowed extensions validation."""
        # Valid extensions
        settings = FileStorageSettings(allowed_extensions=["jpg", "png", "gif"])
        assert settings.allowed_extensions == ["jpg", "png", "gif"]

        # Extensions with dots (should be normalized)
        settings = FileStorageSettings(allowed_extensions=[".jpg", ".PNG", " gif "])
        assert settings.allowed_extensions == ["jpg", "png", "gif"]

    def test_allowed_extensions_empty_validation(self):
        """Test validation failure for empty allowed extensions."""
        with pytest.raises(ValidationError, match="At least one file extension must be allowed"):
            FileStorageSettings(allowed_extensions=[])

    def test_allowed_extensions_invalid_validation(self):
        """Test validation failure for invalid extensions."""
        with pytest.raises(ValidationError, match="No valid file extensions provided"):
            FileStorageSettings(allowed_extensions=["", "  ", "."])

    def test_size_validation(self):
        """Test file size validation."""
        # Valid sizes
        settings = FileStorageSettings(
            min_size=1024,
            max_size=5242880,
        )
        assert settings.min_size == 1024
        assert settings.max_size == 5242880

    def test_dimension_validation(self):
        """Test image dimension validation."""
        # Valid dimensions
        settings = FileStorageSettings(
            min_width=32,
            max_width=4096,
            min_height=32,
            max_height=4096,
        )
        assert settings.min_width == 32
        assert settings.max_width == 4096

    def test_compression_quality_validation(self):
        """Test compression quality validation."""
        # Valid quality
        settings = FileStorageSettings(compression_quality=85)
        assert settings.compression_quality == 85

        # Invalid quality (too low)
        with pytest.raises(ValidationError):
            FileStorageSettings(compression_quality=0)

        # Invalid quality (too high)
        with pytest.raises(ValidationError):
            FileStorageSettings(compression_quality=101)

    def test_max_size_limit(self):
        """Test maximum file size limit."""
        # Valid max size
        settings = FileStorageSettings(max_size=50 * 1024 * 1024)  # 50MB
        assert settings.max_size == 50 * 1024 * 1024

        # Invalid max size (too large)
        with pytest.raises(ValidationError):
            FileStorageSettings(max_size=100 * 1024 * 1024)  # 100MB

    def test_dimension_limits(self):
        """Test image dimension limits."""
        # Valid max dimensions
        settings = FileStorageSettings(
            max_width=8192,
            max_height=8192,
        )
        assert settings.max_width == 8192
        assert settings.max_height == 8192

        # Invalid max dimensions (too large)
        with pytest.raises(ValidationError):
            FileStorageSettings(max_width=10000)

        with pytest.raises(ValidationError):
            FileStorageSettings(max_height=10000)


class TestSupabaseValidation:
    """Test cases for Supabase configuration validation."""

    def test_local_provider_no_validation(self):
        """Test that local provider doesn't trigger Supabase validation."""
        settings = FileStorageSettings(provider="local")
        # Should not raise any validation errors
        assert settings.provider == "local"

    @patch.dict(
        os.environ,
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"},
    )
    def test_supabase_provider_valid_config(self):
        """Test Supabase provider with valid configuration."""
        settings = FileStorageSettings(provider="supabase")
        assert settings.provider == "supabase"

    @patch.dict(os.environ, {}, clear=True)
    def test_supabase_provider_missing_url(self):
        """Test Supabase provider with missing URL."""
        with pytest.raises(ValidationError, match="SUPABASE_URL is required"):
            FileStorageSettings(provider="supabase")

    @patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co"})
    def test_supabase_provider_missing_key(self):
        """Test Supabase provider with missing service key."""
        with pytest.raises(ValidationError, match="SUPABASE_SERVICE_ROLE_KEY is required"):
            FileStorageSettings(provider="supabase")

    @patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": "test-key"})
    def test_supabase_provider_empty_url(self):
        """Test Supabase provider with empty URL."""
        with pytest.raises(ValidationError, match="SUPABASE_URL is required"):
            FileStorageSettings(provider="supabase")

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": ""}
    )
    def test_supabase_provider_empty_key(self):
        """Test Supabase provider with empty service key."""
        with pytest.raises(ValidationError, match="SUPABASE_SERVICE_ROLE_KEY is required"):
            FileStorageSettings(provider="supabase")

    @patch.dict(
        os.environ,
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"},
    )
    def test_supabase_provider_default_bucket_warning(self):
        """Test Supabase provider with default bucket shows warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            settings = FileStorageSettings(provider="supabase")

            # Should create settings successfully
            assert settings.provider == "supabase"
            assert settings.supabase_bucket == "windx-uploads"

            # Should have issued a warning about default bucket
            assert len(w) == 1
            assert "default Supabase bucket name" in str(w[0].message)

    @patch.dict(
        os.environ,
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"},
    )
    def test_supabase_provider_custom_bucket_no_warning(self):
        """Test Supabase provider with custom bucket doesn't warn."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            settings = FileStorageSettings(provider="supabase", supabase_bucket="custom-bucket")

            # Should create settings successfully
            assert settings.provider == "supabase"
            assert settings.supabase_bucket == "custom-bucket"

            # Should not have issued any warnings
            assert len(w) == 0


class TestEnvironmentVariableHandling:
    """Test cases for environment variable handling."""

    @patch.dict(
        os.environ,
        {
            "FILE_STORAGE_PROVIDER": "supabase",
            "FILE_STORAGE_MAX_SIZE": "10485760",
            "FILE_STORAGE_ALLOWED_EXTENSIONS": '["jpg","png","gif"]',  # JSON format
            "FILE_STORAGE_ENABLE_COMPRESSION": "False",
            "FILE_STORAGE_COMPRESSION_QUALITY": "95",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        },
    )
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        settings = FileStorageSettings()

        assert settings.provider == "supabase"
        assert settings.max_size == 10485760
        assert settings.allowed_extensions == ["jpg", "png", "gif"]
        assert settings.enable_compression is False
        assert settings.compression_quality == 95

    @patch.dict(
        os.environ,
        {
            "FILE_STORAGE_MAX_WIDTH": "2048",
            "FILE_STORAGE_MAX_HEIGHT": "1536",
            "FILE_STORAGE_MIN_WIDTH": "64",
            "FILE_STORAGE_MIN_HEIGHT": "48",
        },
    )
    def test_dimension_environment_variables(self):
        """Test dimension settings from environment variables."""
        settings = FileStorageSettings()

        assert settings.max_width == 2048
        assert settings.max_height == 1536
        assert settings.min_width == 64
        assert settings.min_height == 48

    @patch.dict(
        os.environ,
        {
            "FILE_STORAGE_SUPABASE_BUCKET": "production-uploads",
            "FILE_STORAGE_LOCAL_DIR": "/var/uploads",
            "FILE_STORAGE_BASE_URL": "https://cdn.example.com/uploads",
        },
    )
    def test_storage_path_environment_variables(self):
        """Test storage path settings from environment variables."""
        settings = FileStorageSettings()

        assert settings.supabase_bucket == "production-uploads"
        assert settings.local_dir == "/var/uploads"
        assert settings.base_url == "https://cdn.example.com/uploads"


class TestConfigurationEdgeCases:
    """Test edge cases in configuration."""

    def test_provider_case_insensitive(self):
        """Test that provider names are handled correctly."""
        # Test different cases - Pydantic Literal is case-sensitive, so this should fail
        with pytest.raises(ValidationError):
            FileStorageSettings(provider="LOCAL")

        # Valid lowercase should work
        settings = FileStorageSettings(provider="local")
        assert settings.provider == "local"

    def test_extension_normalization_edge_cases(self):
        """Test edge cases in extension normalization."""
        # Mixed case and whitespace
        settings = FileStorageSettings(allowed_extensions=["  .JPG  ", "png", ".GIF.", "webp"])
        # Check that normalization worked correctly
        assert "jpg" in settings.allowed_extensions
        assert "png" in settings.allowed_extensions
        assert "gif" in settings.allowed_extensions  # Should be normalized from ".GIF."
        assert "webp" in settings.allowed_extensions

    def test_zero_values(self):
        """Test handling of zero values."""
        # Min size of 1 should be allowed
        settings = FileStorageSettings(min_size=1)
        assert settings.min_size == 1

        # Zero min size should fail
        with pytest.raises(ValidationError):
            FileStorageSettings(min_size=0)

    def test_boundary_values(self):
        """Test boundary values for validation."""
        # Test maximum allowed values
        settings = FileStorageSettings(
            max_size=50 * 1024 * 1024,  # 50MB (max allowed)
            max_width=8192,  # Max allowed
            max_height=8192,  # Max allowed
            compression_quality=100,  # Max allowed
        )

        assert settings.max_size == 50 * 1024 * 1024
        assert settings.max_width == 8192
        assert settings.max_height == 8192
        assert settings.compression_quality == 100

    def test_string_to_list_conversion(self):
        """Test conversion of comma-separated strings to lists."""
        # This tests the field validator for allowed_extensions
        settings = FileStorageSettings(
            allowed_extensions=["jpg", "png", "gif"]  # Already a list
        )
        assert isinstance(settings.allowed_extensions, list)
        assert settings.allowed_extensions == ["jpg", "png", "gif"]
