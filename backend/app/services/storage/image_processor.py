"""Image processing utilities for file storage.

This module provides image validation, resizing, compression, and format
conversion capabilities for the file storage system.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from app.core.config import FileStorageSettings

try:
    from PIL import Image, ImageOps

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImageInfo(NamedTuple):
    """Information about an image file."""

    width: int
    height: int
    format: str
    mode: str
    size_bytes: int


class ImageProcessingResult(NamedTuple):
    """Result of image processing operation."""

    success: bool
    processed_data: bytes | None = None
    original_info: ImageInfo | None = None
    processed_info: ImageInfo | None = None
    error: str | None = None


class ImageProcessor:
    """Image processing utility class.

    Provides image validation, resizing, compression, and format conversion
    capabilities using PIL/Pillow.
    """

    def __init__(self, settings: FileStorageSettings):
        """Initialize the image processor.

        Args:
            settings: File storage configuration settings

        Raises:
            ImportError: If PIL/Pillow is not available
        """
        if not PIL_AVAILABLE:
            raise ImportError(
                "PIL/Pillow is required for image processing. Install with: pip install Pillow"
            )

        self.settings = settings

    def validate_image(self, image_data: bytes) -> ImageProcessingResult:
        """Validate image data and get information.

        Args:
            image_data: Raw image data

        Returns:
            ImageProcessingResult: Validation result with image info
        """
        try:
            # Open image from bytes
            with Image.open(io.BytesIO(image_data)) as img:
                # Get image information
                info = ImageInfo(
                    width=img.width,
                    height=img.height,
                    format=img.format or "UNKNOWN",
                    mode=img.mode,
                    size_bytes=len(image_data),
                )

                # Validate dimensions
                if img.width < self.settings.min_width:
                    return ImageProcessingResult(
                        success=False,
                        original_info=info,
                        error=f"Image width {img.width}px is below minimum {self.settings.min_width}px",
                    )

                if img.height < self.settings.min_height:
                    return ImageProcessingResult(
                        success=False,
                        original_info=info,
                        error=f"Image height {img.height}px is below minimum {self.settings.min_height}px",
                    )

                if img.width > self.settings.max_width and not self.settings.auto_resize:
                    return ImageProcessingResult(
                        success=False,
                        original_info=info,
                        error=f"Image width {img.width}px exceeds maximum {self.settings.max_width}px",
                    )

                if img.height > self.settings.max_height and not self.settings.auto_resize:
                    return ImageProcessingResult(
                        success=False,
                        original_info=info,
                        error=f"Image height {img.height}px exceeds maximum {self.settings.max_height}px",
                    )

                return ImageProcessingResult(
                    success=True,
                    original_info=info,
                )

        except Exception as e:
            return ImageProcessingResult(
                success=False,
                error=f"Invalid image data: {str(e)}",
            )

    def process_image(self, image_data: bytes, filename: str) -> ImageProcessingResult:
        """Process image with resizing and compression.

        Args:
            image_data: Raw image data
            filename: Original filename (used for format detection)

        Returns:
            ImageProcessingResult: Processing result with processed data
        """
        try:
            # First validate the image
            validation_result = self.validate_image(image_data)
            if not validation_result.success:
                return validation_result

            original_info = validation_result.original_info
            if not original_info:
                return ImageProcessingResult(
                    success=False,
                    error="Failed to get original image information",
                )

            # Open image for processing
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if necessary (for JPEG output)
                if img.mode in ("RGBA", "LA", "P"):
                    # Create white background for transparency
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Auto-orient image based on EXIF data
                img = ImageOps.exif_transpose(img)

                # Resize if needed
                needs_resize = self.settings.auto_resize and (
                    img.width > self.settings.max_width or img.height > self.settings.max_height
                )

                if needs_resize:
                    # Calculate new size maintaining aspect ratio
                    img.thumbnail(
                        (self.settings.max_width, self.settings.max_height),
                        Image.Resampling.LANCZOS,
                    )

                # Determine output format
                output_format = self._get_output_format(filename, img.format)

                # Save processed image
                output_buffer = io.BytesIO()
                save_kwargs = {"format": output_format}

                # Add compression settings for JPEG
                if output_format == "JPEG" and self.settings.enable_compression:
                    save_kwargs.update(
                        {
                            "quality": self.settings.compression_quality,
                            "optimize": True,
                        }
                    )

                img.save(output_buffer, **save_kwargs)
                processed_data = output_buffer.getvalue()

                # Get processed image info
                processed_info = ImageInfo(
                    width=img.width,
                    height=img.height,
                    format=output_format,
                    mode=img.mode,
                    size_bytes=len(processed_data),
                )

                return ImageProcessingResult(
                    success=True,
                    processed_data=processed_data,
                    original_info=original_info,
                    processed_info=processed_info,
                )

        except Exception as e:
            return ImageProcessingResult(
                success=False,
                original_info=validation_result.original_info,
                error=f"Image processing failed: {str(e)}",
            )

    def _get_output_format(self, filename: str, original_format: str | None) -> str:
        """Determine the best output format for the image.

        Args:
            filename: Original filename
            original_format: Original image format

        Returns:
            str: Output format (JPEG, PNG, WEBP, etc.)
        """
        # Get file extension
        extension = filename.lower().split(".")[-1] if "." in filename else ""

        # Map extensions to PIL formats
        format_map = {
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "png": "PNG",
            "webp": "WEBP",
            "gif": "GIF",
            "svg": "SVG",  # Note: PIL doesn't handle SVG well
        }

        # Use extension-based format if available
        if extension in format_map:
            return format_map[extension]

        # Fall back to original format
        if original_format and original_format.upper() in ["JPEG", "PNG", "WEBP", "GIF"]:
            return original_format.upper()

        # Default to JPEG for unknown formats
        return "JPEG"

    def get_image_info(self, image_data: bytes) -> ImageInfo | None:
        """Get information about an image without processing it.

        Args:
            image_data: Raw image data

        Returns:
            ImageInfo | None: Image information or None if invalid
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return ImageInfo(
                    width=img.width,
                    height=img.height,
                    format=img.format or "UNKNOWN",
                    mode=img.mode,
                    size_bytes=len(image_data),
                )
        except Exception:
            return None

    def is_image_file(self, filename: str) -> bool:
        """Check if a filename represents an image file.

        Args:
            filename: Filename to check

        Returns:
            bool: True if filename has an image extension
        """
        if not filename or "." not in filename:
            return False

        extension = filename.lower().split(".")[-1]
        image_extensions = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "tiff", "tif"}
        return extension in image_extensions
