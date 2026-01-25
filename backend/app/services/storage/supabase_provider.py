"""Supabase Storage provider.

This module implements file storage using Supabase Storage buckets.
Suitable for production deployments with cloud storage needs.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from .base import StorageProvider, UploadResult

if TYPE_CHECKING:
    from app.core.config import FileStorageSettings

try:
    from supabase import create_client, Client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class SupabaseStorageProvider(StorageProvider):
    """Supabase Storage provider.

    Stores files in Supabase Storage buckets with automatic URL generation
    and public access configuration.
    """

    def __init__(self, settings: FileStorageSettings, supabase_url: str, supabase_key: str):
        """Initialize the Supabase storage provider.

        Args:
            settings: File storage configuration settings
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key

        Raises:
            ImportError: If supabase-py is not installed
            ValueError: If Supabase credentials are missing
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError(
                "supabase-py is required for Supabase storage. Install with: pip install supabase"
            )

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL and service role key are required")

        self.settings = settings
        self.bucket_name = settings.supabase_bucket

        # Initialize Supabase client
        self.client: Client = create_client(supabase_url, supabase_key)

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the storage bucket exists and is properly configured."""
        try:
            # Try to get bucket info
            buckets = self.client.storage.list_buckets()
            bucket_exists = any(bucket.name == self.bucket_name for bucket in buckets)

            if not bucket_exists:
                # Create bucket with public access
                self.client.storage.create_bucket(self.bucket_name, options={"public": True})
        except Exception as e:
            # Log warning but don't fail initialization
            print(f"Warning: Could not verify/create Supabase bucket: {e}")

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> UploadResult:
        """Upload a file to Supabase Storage.

        Args:
            file_content: The file content as bytes
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            UploadResult: Result of the upload operation
        """
        try:
            # Generate unique filename
            file_path = Path(filename)
            file_extension = file_path.suffix.lower()
            unique_filename = f"profile_images/upload_{uuid.uuid4().hex[:12]}{file_extension}"

            # Upload to Supabase Storage
            response = self.client.storage.from_(self.bucket_name).upload(
                path=unique_filename,
                file=file_content,
                file_options={
                    "content-type": content_type or "application/octet-stream",
                    "upsert": True,  # Allow overwriting
                },
            )

            if hasattr(response, "error") and response.error:
                return UploadResult(
                    success=False,
                    error=f"Supabase upload error: {response.error}",
                )

            # Generate public URL
            url_response = self.client.storage.from_(self.bucket_name).get_public_url(
                unique_filename
            )

            return UploadResult(
                success=True,
                filename=unique_filename,
                url=url_response,
                size=len(file_content),
            )

        except Exception as e:
            return UploadResult(
                success=False,
                error=f"Failed to upload to Supabase: {str(e)}",
            )

    async def delete_file(self, filename: str) -> bool:
        """Delete a file from Supabase Storage.

        Args:
            filename: Name of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            response = self.client.storage.from_(self.bucket_name).remove([filename])
            return not (hasattr(response, "error") and response.error)
        except Exception:
            return False

    async def get_file_url(self, filename: str) -> str | None:
        """Get the public URL for a file.

        Args:
            filename: Name of the file

        Returns:
            str | None: Public URL if file exists
        """
        try:
            # Check if file exists first
            if not await self.file_exists(filename):
                return None

            # Get public URL
            url = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            return url
        except Exception:
            return None

    async def file_exists(self, filename: str) -> bool:
        """Check if a file exists in Supabase Storage.

        Args:
            filename: Name of the file to check

        Returns:
            bool: True if file exists
        """
        try:
            # Try to get file info
            response = self.client.storage.from_(self.bucket_name).list(
                path=str(Path(filename).parent),
                options={"limit": 1000},  # Reasonable limit for checking
            )

            if hasattr(response, "error") and response.error:
                return False

            # Check if filename exists in the list
            file_name = Path(filename).name
            return any(item.get("name") == file_name for item in response if isinstance(item, dict))
        except Exception:
            return False

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            str: Provider name
        """
        return "supabase"
