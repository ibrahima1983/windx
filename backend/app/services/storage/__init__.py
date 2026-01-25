"""File storage services package.

This package provides file storage services with a strategy pattern
for different storage providers (Supabase, local, Azure, etc.).

Public Classes:
    FileStorageService: Main file storage service with provider strategy
    StorageProvider: Abstract base class for storage providers
    LocalStorageProvider: Local filesystem storage provider
    SupabaseStorageProvider: Supabase Storage provider
    ImageProcessor: Image processing utilities (optional)

Public Functions:
    get_storage_service: Get configured storage service instance

Features:
    - Strategy pattern for multiple storage providers
    - Type-safe file operations
    - Automatic provider selection based on configuration
    - File validation and security
    - URL generation for file access
    - Image processing and optimization (with PIL/Pillow)
"""

from .base import StorageProvider, UploadResult
from .local_provider import LocalStorageProvider
from .service import FileStorageService, get_storage_service
from .supabase_provider import SupabaseStorageProvider

# Optional image processing
try:
    from .image_processor import ImageProcessor, ImageInfo, ImageProcessingResult

    __all__ = [
        "StorageProvider",
        "UploadResult",
        "LocalStorageProvider",
        "SupabaseStorageProvider",
        "FileStorageService",
        "get_storage_service",
        "ImageProcessor",
        "ImageInfo",
        "ImageProcessingResult",
    ]
except ImportError:
    __all__ = [
        "StorageProvider",
        "UploadResult",
        "LocalStorageProvider",
        "SupabaseStorageProvider",
        "FileStorageService",
        "get_storage_service",
    ]
