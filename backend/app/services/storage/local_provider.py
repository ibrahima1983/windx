"""Local filesystem storage provider.

This module implements file storage using the local filesystem.
Suitable for development and small deployments.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from .base import StorageProvider, UploadResult

if TYPE_CHECKING:
    from app.core.config import FileStorageSettings


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider.

    Stores files in a local directory and serves them via static file serving.
    """

    def __init__(self, settings: FileStorageSettings):
        """Initialize the local storage provider.

        Args:
            settings: File storage configuration settings
        """
        self.settings = settings
        self.storage_dir = Path(settings.local_dir)

        # Create storage directory if it doesn't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> UploadResult:
        """Upload a file to local storage.

        Args:
            file_content: The file content as bytes
            filename: Original filename
            content_type: MIME type (not used for local storage)

        Returns:
            UploadResult: Result of the upload operation
        """
        try:
            # Generate unique filename
            file_path = Path(filename)
            file_extension = file_path.suffix.lower()
            unique_filename = f"upload_{uuid.uuid4().hex[:12]}{file_extension}"

            # Write file to storage directory
            file_path = self.storage_dir / unique_filename
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Generate URL
            url = f"{self.settings.base_url}/{unique_filename}"

            return UploadResult(
                success=True,
                filename=unique_filename,
                url=url,
                size=len(file_content),
            )

        except Exception as e:
            return UploadResult(
                success=False,
                error=f"Failed to upload file: {str(e)}",
            )

    async def delete_file(self, filename: str) -> bool:
        """Delete a file from local storage.

        Args:
            filename: Name of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            file_path = self.storage_dir / filename
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    async def get_file_url(self, filename: str) -> str | None:
        """Get the public URL for a file.

        Args:
            filename: Name of the file

        Returns:
            str | None: Public URL if file exists
        """
        file_path = self.storage_dir / filename
        if file_path.exists():
            return f"{self.settings.base_url}/{filename}"
        return None

    async def file_exists(self, filename: str) -> bool:
        """Check if a file exists in local storage.

        Args:
            filename: Name of the file to check

        Returns:
            bool: True if file exists
        """
        file_path = self.storage_dir / filename
        return file_path.exists()

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            str: Provider name
        """
        return "local"
