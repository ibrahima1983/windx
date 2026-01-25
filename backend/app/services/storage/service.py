"""Main file storage service with provider strategy.

This module provides the main FileStorageService class that uses
the strategy pattern to delegate to different storage providers.
"""

from __future__ import annotations

import mimetypes
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import UploadFile

from app.core.config import get_settings

from .base import StorageProvider, UploadResult
from .local_provider import LocalStorageProvider
from .supabase_provider import SupabaseStorageProvider

if TYPE_CHECKING:
    from app.core.config import FileStorageSettings

# Try to import image processor (optional dependency)
try:
    from .image_processor import ImageProcessor

    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False


class FileStorageService:
    """Main file storage service using strategy pattern.

    This service provides a unified interface for file operations
    while delegating to different storage providers based on configuration.
    """

    def __init__(self, provider: StorageProvider):
        """Initialize the file storage service.

        Args:
            provider: Storage provider implementation
        """
        self.provider = provider
        self.settings = get_settings().file_storage

        # Initialize image processor if available and image processing is enabled
        self.image_processor = None
        if IMAGE_PROCESSING_AVAILABLE and self.settings.is_image_processing_enabled:
            try:
                self.image_processor = ImageProcessor(self.settings)
            except ImportError:
                # PIL not available, image processing disabled
                pass

    async def upload_file(
        self,
        file: Any,  # Accept any file-like object with read() and filename
        filename: str | None = None,
    ) -> UploadResult:
        """Upload a file using the configured provider.

        Args:
            file: File to upload (UploadFile or bytes)
            filename: Optional filename override

        Returns:
            UploadResult: Result of the upload operation
        """
        print(f"🦆 [STORAGE DEBUG] upload_file called")
        print(f"🦆 [STORAGE DEBUG] file type: {type(file)}")
        print(f"🦆 [STORAGE DEBUG] filename: {filename}")

        # Handle different file input types
        if hasattr(file, "read") and hasattr(file, "filename"):
            print(f"🦆 [STORAGE DEBUG] Processing UploadFile-like object...")
            file_content = await file.read()
            file_name = filename or file.filename or "unknown"
            content_type = getattr(file, "content_type", None)
            print(f"🦆 [STORAGE DEBUG] file_content type: {type(file_content)}")
            print(f"🦆 [STORAGE DEBUG] file_content length: {len(file_content)} bytes")
            print(f"🦆 [STORAGE DEBUG] file_name: {file_name}")
            print(f"🦆 [STORAGE DEBUG] content_type: {content_type}")
        else:
            print(f"🦆 [STORAGE DEBUG] Processing bytes...")
            file_content = file
            file_name = filename or "unknown"
            content_type = None
            print(f"🦆 [STORAGE DEBUG] file_content type: {type(file_content)}")
            print(f"🦆 [STORAGE DEBUG] file_content length: {len(file_content)} bytes")

        # Validate file
        print(f"🦆 [STORAGE DEBUG] Validating file...")
        validation_result = self._validate_file(file_content, file_name)
        if not validation_result.success:
            print(f"🦆 [STORAGE DEBUG] ❌ Validation failed: {validation_result.error}")
            return validation_result

        print(f"🦆 [STORAGE DEBUG] ✅ Validation passed")

        # Process image if it's an image file and processing is enabled
        processed_content = file_content
        if self.image_processor and self._is_image_file(file_name):
            print(f"🦆 [STORAGE DEBUG] Processing image...")
            print(f"🦆 [STORAGE DEBUG] Calling image_processor.process_image with:")
            print(f"🦆 [STORAGE DEBUG] - file_content type: {type(file_content)}")
            print(f"🦆 [STORAGE DEBUG] - file_name: {file_name}")

            processing_result = self.image_processor.process_image(file_content, file_name)

            print(f"🦆 [STORAGE DEBUG] Image processing result: {processing_result}")

            if not processing_result.success:
                print(f"🦆 [STORAGE DEBUG] ❌ Image processing failed: {processing_result.error}")
                return UploadResult(
                    success=False,
                    error=processing_result.error or "Image processing failed",
                )

            if processing_result.processed_data:
                processed_content = processing_result.processed_data

                # Update filename extension if format changed
                if processing_result.processed_info and processing_result.original_info:
                    original_format = processing_result.original_info.format
                    processed_format = processing_result.processed_info.format

                    if original_format != processed_format:
                        # Update file extension to match new format
                        file_path = Path(file_name)
                        new_extension = self._format_to_extension(processed_format)
                        file_name = f"{file_path.stem}.{new_extension}"

        # Guess content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(file_name)

        print(f"🦆 [STORAGE DEBUG] Uploading to provider...")
        print(f"🦆 [STORAGE DEBUG] - processed_content type: {type(processed_content)}")
        print(f"🦆 [STORAGE DEBUG] - processed_content length: {len(processed_content)} bytes")
        print(f"🦆 [STORAGE DEBUG] - final file_name: {file_name}")
        print(f"🦆 [STORAGE DEBUG] - content_type: {content_type}")

        # Upload using provider
        return await self.provider.upload_file(
            file_content=processed_content,
            filename=file_name,
            content_type=content_type,
        )

    async def delete_file(self, filename: str) -> bool:
        """Delete a file using the configured provider.

        Args:
            filename: Name of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        return await self.provider.delete_file(filename)

    async def get_file_url(self, filename: str) -> str | None:
        """Get the public URL for a file.

        Args:
            filename: Name of the file

        Returns:
            str | None: Public URL if file exists
        """
        return await self.provider.get_file_url(filename)

    async def file_exists(self, filename: str) -> bool:
        """Check if a file exists.

        Args:
            filename: Name of the file to check

        Returns:
            bool: True if file exists
        """
        return await self.provider.file_exists(filename)

    def get_provider_info(self) -> dict[str, str]:
        """Get information about the current provider.

        Returns:
            dict: Provider information
        """
        info = {
            "provider": self.provider.get_provider_name(),
            "description": f"Using {self.provider.get_provider_name()} storage provider",
            "image_processing": "enabled" if self.image_processor else "disabled",
        }

        if self.image_processor:
            info.update(
                {
                    "max_dimensions": f"{self.settings.max_width}x{self.settings.max_height}",
                    "min_dimensions": f"{self.settings.min_width}x{self.settings.min_height}",
                    "compression": "enabled" if self.settings.enable_compression else "disabled",
                    "auto_resize": "enabled" if self.settings.auto_resize else "disabled",
                }
            )

        return info

    def _validate_file(self, file_content: bytes, filename: str) -> UploadResult:
        """Validate file content and name.

        Args:
            file_content: File content to validate
            filename: Filename to validate

        Returns:
            UploadResult: Validation result
        """
        settings = get_settings()

        # Check file size (minimum)
        if len(file_content) < settings.file_storage.min_size:
            min_kb = settings.file_storage.min_size_kb
            return UploadResult(
                success=False,
                error=f"File too small. Minimum size is {min_kb:.1f}KB",
            )

        # Check file size (maximum)
        if len(file_content) > settings.file_storage.max_size:
            max_mb = settings.file_storage.max_size_mb
            return UploadResult(
                success=False,
                error=f"File too large. Maximum size is {max_mb:.1f}MB",
            )

        # Check file extension
        file_path = Path(filename)
        file_extension = file_path.suffix.lower().lstrip(".")

        if file_extension not in settings.file_storage.allowed_extensions:
            allowed = ", ".join(settings.file_storage.allowed_extensions)
            return UploadResult(
                success=False,
                error=f"File type not allowed. Allowed types: {allowed}",
            )

        # Basic content validation (check for empty files)
        if len(file_content) == 0:
            return UploadResult(
                success=False,
                error="File is empty",
            )

        return UploadResult(success=True)

    def _is_image_file(self, filename: str) -> bool:
        """Check if a filename represents an image file.

        Args:
            filename: Filename to check

        Returns:
            bool: True if filename has an image extension
        """
        if self.image_processor:
            return self.image_processor.is_image_file(filename)

        # Fallback check without image processor
        if not filename or "." not in filename:
            return False

        extension = filename.lower().split(".")[-1]
        image_extensions = {"jpg", "jpeg", "png", "gif", "webp", "svg"}
        return extension in image_extensions

    def _format_to_extension(self, format_name: str) -> str:
        """Convert PIL format name to file extension.

        Args:
            format_name: PIL format name (e.g., 'JPEG', 'PNG')

        Returns:
            str: File extension (e.g., 'jpg', 'png')
        """
        format_map = {
            "JPEG": "jpg",
            "PNG": "png",
            "WEBP": "webp",
            "GIF": "gif",
            "BMP": "bmp",
            "TIFF": "tiff",
        }
        return format_map.get(format_name.upper(), "jpg")


def _create_storage_provider(settings: FileStorageSettings) -> StorageProvider:
    """Create a storage provider based on configuration.

    Args:
        settings: File storage configuration

    Returns:
        StorageProvider: Configured storage provider

    Raises:
        ValueError: If provider is not supported or configuration is invalid
    """
    provider_name = settings.provider.lower()

    if provider_name == "local":
        return LocalStorageProvider(settings)

    elif provider_name == "supabase":
        app_settings = get_settings()

        # Check if Supabase configuration is available
        supabase_url = app_settings.supabase_url
        supabase_key = app_settings.supabase_service_role_key

        if not supabase_url:
            raise ValueError("SUPABASE_URL is required when using supabase storage provider")

        if not supabase_key:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY is required when using supabase storage provider"
            )

        # Convert SecretStr to string if needed
        key_str = (
            supabase_key.get_secret_value()
            if hasattr(supabase_key, "get_secret_value")
            else str(supabase_key)
        )

        return SupabaseStorageProvider(settings, supabase_url, key_str)

    else:
        raise ValueError(
            f"Unsupported storage provider: {provider_name}. Supported providers: local, supabase"
        )


@lru_cache(maxsize=1)
def get_storage_service() -> FileStorageService:
    """Get a cached file storage service instance.

    Returns:
        FileStorageService: Configured storage service
    """
    settings = get_settings()
    provider = _create_storage_provider(settings.file_storage)
    return FileStorageService(provider)
