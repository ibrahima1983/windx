"""Base storage provider interface.

This module defines the abstract base class for all storage providers
and common data structures used across the storage system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class UploadResult:
    """Result of a file upload operation.

    Attributes:
        success: Whether the upload was successful
        filename: The stored filename (may be different from original)
        url: Public URL to access the file
        size: File size in bytes
        error: Error message if upload failed
    """

    success: bool
    filename: str | None = None
    url: str | None = None
    size: int | None = None
    error: str | None = None


class StorageProvider(ABC):
    """Abstract base class for file storage providers.

    This class defines the interface that all storage providers must implement.
    It follows the strategy pattern to allow switching between different
    storage backends (local, Supabase, Azure, etc.).
    """

    @abstractmethod
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> UploadResult:
        """Upload a file to the storage provider.

        Args:
            file_content: The file content as bytes
            filename: Original filename (will be processed for uniqueness)
            content_type: MIME type of the file

        Returns:
            UploadResult: Result of the upload operation
        """
        pass

    @abstractmethod
    async def delete_file(self, filename: str) -> bool:
        """Delete a file from the storage provider.

        Args:
            filename: Name of the file to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_file_url(self, filename: str) -> str | None:
        """Get the public URL for a file.

        Args:
            filename: Name of the file

        Returns:
            str | None: Public URL if file exists, None otherwise
        """
        pass

    @abstractmethod
    async def file_exists(self, filename: str) -> bool:
        """Check if a file exists in storage.

        Args:
            filename: Name of the file to check

        Returns:
            bool: True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this storage provider.

        Returns:
            str: Provider name (e.g., 'local', 'supabase', 'azure')
        """
        pass
