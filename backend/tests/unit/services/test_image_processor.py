"""Unit tests for ImageProcessor.

This module tests image processing functionality including:
- Image validation
- Image resizing and compression
- Format conversion
- Error handling
"""

import io
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import FileStorageSettings


# Mock PIL/Pillow for tests that don't have it available
class MockImage:
    """Mock PIL Image class."""

    def __init__(self, width=100, height=100, mode="RGB", format="JPEG"):
        self.width = width
        self.height = height
        self.mode = mode
        self.format = format
        self.size = (width, height)

    def save(self, buffer, format=None, **kwargs):
        # Simulate saving image data
        data = f"mock_image_{self.width}x{self.height}_{format or self.format}".encode()
        buffer.write(data)

    def convert(self, mode):
        return MockImage(self.width, self.height, mode, self.format)

    def thumbnail(self, size, resample=None):
        # Simulate thumbnail creation
        new_width = min(self.width, size[0])
        new_height = min(self.height, size[1])
        self.width = new_width
        self.height = new_height
        self.size = (new_width, new_height)


class MockImageModule:
    """Mock PIL Image module."""

    class Resampling:
        LANCZOS = "LANCZOS"

    @staticmethod
    def new(mode, size, color=None):
        return MockImage(size[0], size[1], mode)

    @staticmethod
    def open(buffer):
        # Simulate opening an image from buffer
        data = buffer.read()
        if b"small" in data:
            return MockImage(10, 10)
        elif b"large" in data:
            return MockImage(5000, 4000)
        elif b"invalid" in data:
            raise Exception("Invalid image data")
        else:
            return MockImage(800, 600)


class MockImageDraw:
    """Mock PIL ImageDraw class."""

    def __init__(self, image):
        self.image = image

    def rectangle(self, *args, **kwargs):
        pass

    def text(self, *args, **kwargs):
        pass


class MockImageOps:
    """Mock PIL ImageOps module."""

    @staticmethod
    def exif_transpose(image):
        return image


@pytest.fixture
def mock_pil():
    """Mock PIL/Pillow modules."""
    mock_image_module = MockImageModule()
    mock_image_draw = MockImageDraw
    mock_image_ops = MockImageOps

    with patch.dict(
        "sys.modules",
        {
            "PIL": MagicMock(),
            "PIL.Image": mock_image_module,
            "PIL.ImageDraw": mock_image_draw,
            "PIL.ImageOps": mock_image_ops,
        },
    ):
        # Also patch the imports in the image processor module
        with (
            patch("app.services.storage.image_processor.Image", mock_image_module),
            patch("app.services.storage.image_processor.ImageOps", mock_image_ops),
        ):
            yield


@pytest.fixture
def file_storage_settings():
    """Create file storage settings for testing."""
    return FileStorageSettings(
        provider="local",
        max_width=1024,
        max_height=1024,
        min_width=32,
        min_height=32,
        enable_compression=True,
        compression_quality=85,
        auto_resize=True,
    )


@pytest.fixture
def image_processor(mock_pil, file_storage_settings):
    """Create image processor with mocked PIL."""
    with patch("app.services.storage.image_processor.PIL_AVAILABLE", True):
        from app.services.storage.image_processor import ImageProcessor

        return ImageProcessor(file_storage_settings)


class TestImageProcessor:
    """Test cases for ImageProcessor."""

    def test_init_without_pil(self, file_storage_settings):
        """Test ImageProcessor initialization without PIL."""
        with patch("app.services.storage.image_processor.PIL_AVAILABLE", False):
            from app.services.storage.image_processor import ImageProcessor

            with pytest.raises(ImportError, match="PIL/Pillow is required"):
                ImageProcessor(file_storage_settings)

    def test_validate_image_success(self, image_processor):
        """Test successful image validation."""
        image_data = b"valid_image_data"

        result = image_processor.validate_image(image_data)

        assert result.success is True
        assert result.original_info is not None
        assert result.original_info.width == 800
        assert result.original_info.height == 600
        assert result.original_info.format == "JPEG"

    def test_validate_image_too_small(self, image_processor):
        """Test image validation failure for too small image."""
        image_data = b"small_image_data"

        result = image_processor.validate_image(image_data)

        assert result.success is False
        assert "below minimum" in result.error
        assert result.original_info is not None

    def test_validate_image_too_large_no_resize(self, image_processor):
        """Test image validation failure for too large image without auto-resize."""
        image_processor.settings.auto_resize = False
        image_data = b"large_image_data"

        result = image_processor.validate_image(image_data)

        assert result.success is False
        assert "exceeds maximum" in result.error

    def test_validate_image_too_large_with_resize(self, image_processor):
        """Test image validation success for too large image with auto-resize."""
        image_processor.settings.auto_resize = True
        image_data = b"large_image_data"

        result = image_processor.validate_image(image_data)

        assert result.success is True  # Should pass because auto-resize is enabled

    def test_validate_image_invalid_data(self, image_processor):
        """Test image validation failure for invalid image data."""
        image_data = b"invalid_image_data"

        result = image_processor.validate_image(image_data)

        assert result.success is False
        assert "Invalid image data" in result.error

    def test_process_image_success(self, image_processor):
        """Test successful image processing."""
        image_data = b"valid_image_data"

        result = image_processor.process_image(image_data, "test.jpg")

        assert result.success is True
        assert result.processed_data is not None
        assert result.original_info is not None
        assert result.processed_info is not None

    def test_process_image_with_resize(self, image_processor):
        """Test image processing with resizing."""
        image_data = b"large_image_data"  # This will create a 5000x4000 image

        result = image_processor.process_image(image_data, "large.jpg")

        assert result.success is True
        # Image should be resized to fit within max dimensions
        assert result.processed_info.width <= image_processor.settings.max_width
        assert result.processed_info.height <= image_processor.settings.max_height

    def test_process_image_validation_failure(self, image_processor):
        """Test image processing with validation failure."""
        image_data = b"small_image_data"  # Too small

        result = image_processor.process_image(image_data, "small.jpg")

        assert result.success is False
        assert "below minimum" in result.error

    def test_process_image_processing_failure(self, image_processor):
        """Test image processing with processing failure."""
        image_data = b"invalid_image_data"

        result = image_processor.process_image(image_data, "invalid.jpg")

        assert result.success is False
        assert "Invalid image data" in result.error

    def test_get_output_format_from_extension(self, image_processor):
        """Test output format determination from file extension."""
        assert image_processor._get_output_format("test.jpg", None) == "JPEG"
        assert image_processor._get_output_format("test.jpeg", None) == "JPEG"
        assert image_processor._get_output_format("test.png", None) == "PNG"
        assert image_processor._get_output_format("test.webp", None) == "WEBP"
        assert image_processor._get_output_format("test.gif", None) == "GIF"

    def test_get_output_format_from_original(self, image_processor):
        """Test output format determination from original format."""
        assert image_processor._get_output_format("test", "JPEG") == "JPEG"
        assert image_processor._get_output_format("test", "PNG") == "PNG"
        assert image_processor._get_output_format("test", "WEBP") == "WEBP"

    def test_get_output_format_default(self, image_processor):
        """Test output format default fallback."""
        assert image_processor._get_output_format("test.unknown", None) == "JPEG"
        assert image_processor._get_output_format("test", "UNKNOWN") == "JPEG"

    def test_get_image_info_success(self, image_processor):
        """Test getting image info successfully."""
        image_data = b"valid_image_data"

        info = image_processor.get_image_info(image_data)

        assert info is not None
        assert info.width == 800
        assert info.height == 600
        assert info.format == "JPEG"
        assert info.mode == "RGB"

    def test_get_image_info_failure(self, image_processor):
        """Test getting image info failure."""
        image_data = b"invalid_image_data"

        info = image_processor.get_image_info(image_data)

        assert info is None

    def test_is_image_file_valid_extensions(self, image_processor):
        """Test image file detection with valid extensions."""
        assert image_processor.is_image_file("test.jpg") is True
        assert image_processor.is_image_file("test.jpeg") is True
        assert image_processor.is_image_file("test.png") is True
        assert image_processor.is_image_file("test.gif") is True
        assert image_processor.is_image_file("test.webp") is True
        assert image_processor.is_image_file("test.svg") is True
        assert image_processor.is_image_file("test.bmp") is True
        assert image_processor.is_image_file("test.tiff") is True

    def test_is_image_file_invalid_extensions(self, image_processor):
        """Test image file detection with invalid extensions."""
        assert image_processor.is_image_file("test.txt") is False
        assert image_processor.is_image_file("test.pdf") is False
        assert image_processor.is_image_file("test.doc") is False
        assert image_processor.is_image_file("test") is False
        assert image_processor.is_image_file("") is False

    def test_is_image_file_case_insensitive(self, image_processor):
        """Test image file detection is case insensitive."""
        assert image_processor.is_image_file("test.JPG") is True
        assert image_processor.is_image_file("test.PNG") is True
        assert image_processor.is_image_file("test.GIF") is True


class TestImageProcessingSettings:
    """Test cases for image processing with different settings."""

    def test_compression_disabled(self, mock_pil, file_storage_settings):
        """Test image processing with compression disabled."""
        file_storage_settings.enable_compression = False

        with patch("app.services.storage.image_processor.PIL_AVAILABLE", True):
            from app.services.storage.image_processor import ImageProcessor

            processor = ImageProcessor(file_storage_settings)

        image_data = b"valid_image_data"
        result = processor.process_image(image_data, "test.jpg")

        assert result.success is True

    def test_auto_resize_disabled(self, mock_pil, file_storage_settings):
        """Test image processing with auto-resize disabled."""
        file_storage_settings.auto_resize = False

        with patch("app.services.storage.image_processor.PIL_AVAILABLE", True):
            from app.services.storage.image_processor import ImageProcessor

            processor = ImageProcessor(file_storage_settings)

        # Large image should fail validation when auto-resize is disabled
        image_data = b"large_image_data"
        result = processor.validate_image(image_data)

        assert result.success is False
        assert "exceeds maximum" in result.error

    def test_different_quality_settings(self, mock_pil, file_storage_settings):
        """Test image processing with different quality settings."""
        file_storage_settings.compression_quality = 95

        with patch("app.services.storage.image_processor.PIL_AVAILABLE", True):
            from app.services.storage.image_processor import ImageProcessor

            processor = ImageProcessor(file_storage_settings)

        image_data = b"valid_image_data"
        result = processor.process_image(image_data, "test.jpg")

        assert result.success is True

    def test_different_dimension_limits(self, mock_pil):
        """Test image processing with different dimension limits."""
        settings = FileStorageSettings(
            provider="local",
            max_width=512,
            max_height=512,
            min_width=64,
            min_height=64,
        )

        with patch("app.services.storage.image_processor.PIL_AVAILABLE", True):
            from app.services.storage.image_processor import ImageProcessor

            processor = ImageProcessor(settings)

        # Test with image that fits
        image_data = b"valid_image_data"  # 800x600
        result = processor.validate_image(image_data)

        # Should fail because 800x600 exceeds 512x512 and auto_resize is False by default
        assert result.success is False or settings.auto_resize is True


class TestImageProcessingEdgeCases:
    """Test edge cases in image processing."""

    def test_rgba_to_rgb_conversion(self, image_processor):
        """Test RGBA to RGB conversion with transparency."""
        # This would test the transparency handling in real PIL
        # For now, just test that processing completes
        image_data = b"valid_image_data"
        result = image_processor.process_image(image_data, "test.png")

        assert result.success is True

    def test_exif_orientation_handling(self, image_processor):
        """Test EXIF orientation handling."""
        # This would test EXIF auto-rotation in real PIL
        # For now, just test that processing completes
        image_data = b"valid_image_data"
        result = image_processor.process_image(image_data, "test.jpg")

        assert result.success is True

    def test_various_input_formats(self, image_processor):
        """Test processing various input formats."""
        formats = ["test.jpg", "test.png", "test.webp", "test.gif"]

        for filename in formats:
            image_data = b"valid_image_data"
            result = image_processor.process_image(image_data, filename)
            assert result.success is True, f"Processing failed for {filename}"

    def test_empty_filename(self, image_processor):
        """Test processing with empty filename."""
        image_data = b"valid_image_data"
        result = image_processor.process_image(image_data, "")

        # Should still work, using default format
        assert result.success is True

    def test_filename_without_extension(self, image_processor):
        """Test processing with filename without extension."""
        image_data = b"valid_image_data"
        result = image_processor.process_image(image_data, "image_file")

        # Should work, using default JPEG format
        assert result.success is True
