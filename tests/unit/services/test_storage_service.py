"""Unit tests for FileStorageService.

This module tests the main file storage service functionality including:
- Provider strategy pattern
- File validation
- Image processing integration
- Error handling
"""

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.storage import FileStorageService, UploadResult
from app.services.storage.base import StorageProvider


class MockStorageProvider(StorageProvider):
    """Mock storage provider for testing."""

    def __init__(self):
        self.uploaded_files = {}
        self.should_fail = False
        self.fail_message = "Mock upload failed"

    async def upload_file(
        self, file_content: bytes, filename: str, content_type: str | None = None
    ) -> UploadResult:
        if self.should_fail:
            return UploadResult(success=False, error=self.fail_message)

        unique_filename = f"mock_{filename}"
        self.uploaded_files[unique_filename] = file_content

        return UploadResult(
            success=True,
            filename=unique_filename,
            url=f"https://mock.storage/{unique_filename}",
            size=len(file_content),
        )

    async def delete_file(self, filename: str) -> bool:
        if filename in self.uploaded_files:
            del self.uploaded_files[filename]
            return True
        return False

    async def get_file_url(self, filename: str) -> str | None:
        if filename in self.uploaded_files:
            return f"https://mock.storage/{filename}"
        return None

    async def file_exists(self, filename: str) -> bool:
        return filename in self.uploaded_files

    def get_provider_name(self) -> str:
        return "mock"


@pytest.fixture
def mock_provider():
    """Create mock storage provider."""
    return MockStorageProvider()


@pytest.fixture
def storage_service(mock_provider):
    """Create storage service with mock provider and disabled image processing."""
    with patch("app.services.storage.service.IMAGE_PROCESSING_AVAILABLE", False):
        return FileStorageService(mock_provider)


@pytest.fixture
def storage_service_with_image_processing(mock_provider):
    """Create storage service with mock provider and image processing enabled."""
    with patch("app.services.storage.service.IMAGE_PROCESSING_AVAILABLE", True):
        service = FileStorageService(mock_provider)
        # Mock the image processor to avoid real image processing
        service.image_processor = MagicMock()
        return service


@pytest.fixture
def sample_image_data():
    """Create sample image data for testing."""
    # Create a larger valid JPEG-like data that meets minimum size requirement
    jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00"
    jpeg_footer = b"\xff\xd9"
    # Add enough dummy data to exceed 1KB minimum (1024 bytes)
    dummy_data = b"\x00" * 1200  # 1200 bytes of dummy data
    return jpeg_header + dummy_data + jpeg_footer


class TestFileStorageService:
    """Test cases for FileStorageService."""

    def test_init_without_image_processor(self, mock_provider):
        """Test service initialization without image processor."""
        with patch("app.services.storage.service.IMAGE_PROCESSING_AVAILABLE", False):
            service = FileStorageService(mock_provider)
            assert service.provider == mock_provider
            assert service.image_processor is None

    @patch("app.services.storage.service.IMAGE_PROCESSING_AVAILABLE", True)
    @patch("app.services.storage.service.ImageProcessor")
    def test_init_with_image_processor(self, mock_image_processor_class, mock_provider):
        """Test service initialization with image processor."""
        mock_image_processor = MagicMock()
        mock_image_processor_class.return_value = mock_image_processor

        service = FileStorageService(mock_provider)

        assert service.provider == mock_provider
        assert service.image_processor == mock_image_processor
        mock_image_processor_class.assert_called_once()

    async def test_upload_file_bytes_success(self, storage_service, sample_image_data):
        """Test successful file upload with bytes."""
        result = await storage_service.upload_file(file=sample_image_data, filename="test.jpg")

        assert result.success is True
        assert result.filename == "mock_test.jpg"
        assert result.url == "https://mock.storage/mock_test.jpg"
        assert result.size == len(sample_image_data)
        assert result.error is None

    async def test_upload_file_uploadfile_success(self, storage_service, sample_image_data):
        """Test successful file upload with UploadFile."""
        from fastapi import UploadFile

        # Create mock UploadFile
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=sample_image_data)

        result = await storage_service.upload_file(file=mock_file)

        assert result.success is True
        assert result.filename == "mock_test.jpg"
        mock_file.read.assert_called_once()

    async def test_upload_file_validation_failure(self, storage_service):
        """Test file upload with validation failure."""
        # Empty file should fail validation
        result = await storage_service.upload_file(file=b"", filename="empty.jpg")

        assert result.success is False
        assert "too small" in result.error.lower()

    async def test_upload_file_invalid_extension(self, storage_service):
        """Test file upload with invalid extension."""
        # Use larger data to pass size validation
        large_data = b"x" * 2048  # 2KB

        result = await storage_service.upload_file(file=large_data, filename="test.exe")

        assert result.success is False
        assert "not allowed" in result.error.lower()

    async def test_upload_file_too_large(self, storage_service):
        """Test file upload that's too large."""
        # Create a file larger than the default 5MB limit
        large_data = b"x" * (6 * 1024 * 1024)  # 6MB

        result = await storage_service.upload_file(file=large_data, filename="large.jpg")

        assert result.success is False
        assert "too large" in result.error.lower()

    async def test_upload_file_provider_failure(self, storage_service, sample_image_data):
        """Test file upload when provider fails."""
        # Set provider to fail AFTER validation passes
        storage_service.provider.should_fail = True
        storage_service.provider.fail_message = "Storage provider error"

        result = await storage_service.upload_file(file=sample_image_data, filename="test.jpg")

        assert result.success is False
        assert result.error == "Storage provider error"

    async def test_delete_file_success(self, storage_service, sample_image_data):
        """Test successful file deletion."""
        # First upload a file
        await storage_service.upload_file(sample_image_data, "test.jpg")

        # Then delete it
        success = await storage_service.delete_file("mock_test.jpg")
        assert success is True

    async def test_delete_file_not_found(self, storage_service):
        """Test deleting non-existent file."""
        success = await storage_service.delete_file("nonexistent.jpg")
        assert success is False

    async def test_get_file_url_exists(self, storage_service, sample_image_data):
        """Test getting URL for existing file."""
        # Upload file first
        await storage_service.upload_file(sample_image_data, "test.jpg")

        url = await storage_service.get_file_url("mock_test.jpg")
        assert url == "https://mock.storage/mock_test.jpg"

    async def test_get_file_url_not_found(self, storage_service):
        """Test getting URL for non-existent file."""
        url = await storage_service.get_file_url("nonexistent.jpg")
        assert url is None

    async def test_file_exists_true(self, storage_service, sample_image_data):
        """Test file exists check for existing file."""
        # Upload file first
        await storage_service.upload_file(sample_image_data, "test.jpg")

        exists = await storage_service.file_exists("mock_test.jpg")
        assert exists is True

    async def test_file_exists_false(self, storage_service):
        """Test file exists check for non-existent file."""
        exists = await storage_service.file_exists("nonexistent.jpg")
        assert exists is False

    def test_get_provider_info_without_image_processor(self, storage_service):
        """Test getting provider info without image processor."""
        storage_service.image_processor = None

        info = storage_service.get_provider_info()

        assert info["provider"] == "mock"
        assert info["description"] == "Using mock storage provider"
        assert info["image_processing"] == "disabled"

    def test_get_provider_info_with_image_processor(self, storage_service):
        """Test getting provider info with image processor."""
        # Mock image processor
        mock_processor = MagicMock()
        storage_service.image_processor = mock_processor

        info = storage_service.get_provider_info()

        assert info["provider"] == "mock"
        assert info["image_processing"] == "enabled"
        assert "max_dimensions" in info
        assert "compression" in info

    def test_is_image_file_with_processor(self, storage_service):
        """Test image file detection with processor."""
        mock_processor = MagicMock()
        mock_processor.is_image_file.return_value = True
        storage_service.image_processor = mock_processor

        result = storage_service._is_image_file("test.jpg")

        assert result is True
        mock_processor.is_image_file.assert_called_once_with("test.jpg")

    def test_is_image_file_without_processor(self, storage_service):
        """Test image file detection without processor."""
        storage_service.image_processor = None

        # Test various extensions
        assert storage_service._is_image_file("test.jpg") is True
        assert storage_service._is_image_file("test.png") is True
        assert storage_service._is_image_file("test.gif") is True
        assert storage_service._is_image_file("test.txt") is False
        assert storage_service._is_image_file("test") is False

    def test_format_to_extension(self, storage_service):
        """Test format to extension conversion."""
        assert storage_service._format_to_extension("JPEG") == "jpg"
        assert storage_service._format_to_extension("PNG") == "png"
        assert storage_service._format_to_extension("WEBP") == "webp"
        assert storage_service._format_to_extension("UNKNOWN") == "jpg"  # Default

    @patch("app.services.storage.service.IMAGE_PROCESSING_AVAILABLE", True)
    async def test_upload_with_image_processing_success(
        self, storage_service_with_image_processing, sample_image_data
    ):
        """Test file upload with successful image processing."""
        from app.services.storage.image_processor import ImageProcessingResult, ImageInfo

        storage_service = storage_service_with_image_processing
        processed_data = b"processed_image_data"

        storage_service.image_processor.process_image.return_value = ImageProcessingResult(
            success=True,
            processed_data=processed_data,
            original_info=ImageInfo(800, 600, "JPEG", "RGB", len(sample_image_data)),
            processed_info=ImageInfo(400, 300, "JPEG", "RGB", len(processed_data)),
        )

        storage_service._is_image_file = MagicMock(return_value=True)

        result = await storage_service.upload_file(sample_image_data, "test.jpg")

        assert result.success is True
        # Verify processed data was uploaded, not original
        assert storage_service.provider.uploaded_files["mock_test.jpg"] == processed_data
        storage_service.image_processor.process_image.assert_called_once_with(
            sample_image_data, "test.jpg"
        )

    @patch("app.services.storage.service.IMAGE_PROCESSING_AVAILABLE", True)
    async def test_upload_with_image_processing_failure(
        self, storage_service_with_image_processing, sample_image_data
    ):
        """Test file upload with image processing failure."""
        from app.services.storage.image_processor import ImageProcessingResult

        storage_service = storage_service_with_image_processing

        # Mock image processor that fails
        storage_service.image_processor.process_image.return_value = ImageProcessingResult(
            success=False, error="Image processing failed"
        )

        storage_service._is_image_file = MagicMock(return_value=True)

        result = await storage_service.upload_file(sample_image_data, "test.jpg")

        assert result.success is False
        assert result.error == "Image processing failed"

    @patch("app.services.storage.service.IMAGE_PROCESSING_AVAILABLE", True)
    async def test_upload_with_format_change(
        self, storage_service_with_image_processing, sample_image_data
    ):
        """Test file upload with format change during processing."""
        from app.services.storage.image_processor import ImageProcessingResult, ImageInfo

        storage_service = storage_service_with_image_processing
        processed_data = b"processed_webp_data"

        storage_service.image_processor.process_image.return_value = ImageProcessingResult(
            success=True,
            processed_data=processed_data,
            original_info=ImageInfo(800, 600, "JPEG", "RGB", len(sample_image_data)),
            processed_info=ImageInfo(800, 600, "WEBP", "RGB", len(processed_data)),
        )

        storage_service._is_image_file = MagicMock(return_value=True)

        result = await storage_service.upload_file(sample_image_data, "test.jpg")

        assert result.success is True
        # Filename should change to reflect new format
        assert result.filename == "mock_test.webp"


class TestFileValidation:
    """Test cases for file validation."""

    def test_validate_file_success(self, storage_service):
        """Test successful file validation."""
        valid_data = b"x" * 2048  # 2KB file

        result = storage_service._validate_file(valid_data, "test.jpg")

        assert result.success is True
        assert result.error is None

    def test_validate_file_too_small(self, storage_service):
        """Test validation failure for file too small."""
        small_data = b"x" * 100  # 100 bytes (less than 1KB minimum)

        result = storage_service._validate_file(small_data, "test.jpg")

        assert result.success is False
        assert "too small" in result.error.lower()

    def test_validate_file_too_large(self, storage_service):
        """Test validation failure for file too large."""
        large_data = b"x" * (6 * 1024 * 1024)  # 6MB (more than 5MB limit)

        result = storage_service._validate_file(large_data, "test.jpg")

        assert result.success is False
        assert "too large" in result.error.lower()

    def test_validate_file_invalid_extension(self, storage_service):
        """Test validation failure for invalid extension."""
        valid_data = b"x" * 2048

        result = storage_service._validate_file(valid_data, "test.exe")

        assert result.success is False
        assert "not allowed" in result.error.lower()

    def test_validate_file_empty(self, storage_service):
        """Test validation failure for empty file."""
        result = storage_service._validate_file(b"", "test.jpg")

        assert result.success is False
        # Empty files fail the minimum size check, not the empty check
        assert "too small" in result.error.lower()

    def test_validate_file_various_extensions(self, storage_service):
        """Test validation with various allowed extensions."""
        valid_data = b"x" * 2048

        # Test allowed extensions
        for ext in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
            result = storage_service._validate_file(valid_data, f"test.{ext}")
            assert result.success is True, f"Extension {ext} should be allowed"

        # Test disallowed extensions
        for ext in ["txt", "exe", "pdf", "doc"]:
            result = storage_service._validate_file(valid_data, f"test.{ext}")
            assert result.success is False, f"Extension {ext} should not be allowed"
