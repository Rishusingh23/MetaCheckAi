import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional, Tuple

from app.services.storage.base import BaseStorageProvider

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff", "image/bmp"}


class LocalStorageProvider(BaseStorageProvider):
    """
    Local filesystem storage provider with safe path traversal protection.
    """

    def __init__(self, base_directory: Optional[str] = None):
        self.base_dir = os.path.abspath(base_directory or os.path.join(os.getcwd(), "uploads"))
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_safe_path(self, relative_or_absolute_path: str) -> str:
        """
        Ensures target path stays strictly inside base_dir to prevent directory traversal.
        """
        if os.path.isabs(relative_or_absolute_path):
            norm_path = os.path.abspath(relative_or_absolute_path)
        else:
            norm_path = os.path.abspath(os.path.join(self.base_dir, relative_or_absolute_path))

        if not norm_path.startswith(self.base_dir):
            raise ValueError(f"Security error: Path traversal attempt detected for '{relative_or_absolute_path}'")
        return norm_path

    async def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        subfolder: Optional[str] = None,
        directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save file bytes to local filesystem storage.
        Returns metadata dict with storage_path, url, filename, file_size_bytes.
        """
        folder = subfolder or directory or ""
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            ext = ".jpg"

        unique_name = f"{uuid.uuid4()}{ext}"
        target_dir = os.path.join(self.base_dir, folder) if folder else self.base_dir
        target_dir = self._resolve_safe_path(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        full_path = os.path.join(target_dir, unique_name)
        full_path = self._resolve_safe_path(full_path)

        loop = asyncio.get_running_loop()

        def _write():
            with open(full_path, "wb") as f:
                f.write(file_bytes)

        await loop.run_in_executor(None, _write)

        rel_path = os.path.relpath(full_path, self.base_dir)
        logger.info("Stored file successfully: %s (%d bytes)", rel_path, len(file_bytes))

        return {
            "storage_path": full_path,
            "relative_path": rel_path,
            "filename": unique_name,
            "url": f"/uploads/{rel_path}",
            "file_size_bytes": len(file_bytes),
        }

    async def get_file(self, storage_path: str) -> bytes:
        """Retrieve raw file bytes from storage path."""
        safe_path = self._resolve_safe_path(storage_path)
        if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
            raise FileNotFoundError(f"Storage file not found: '{storage_path}'")

        loop = asyncio.get_running_loop()

        def _read():
            with open(safe_path, "rb") as f:
                return f.read()

        return await loop.run_in_executor(None, _read)

    async def read_file(self, storage_path: str) -> bytes:
        """Alias for get_file."""
        return await self.get_file(storage_path)

    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage."""
        try:
            safe_path = self._resolve_safe_path(storage_path)
            if os.path.exists(safe_path) and os.path.isfile(safe_path):
                os.remove(safe_path)
                return True
            return False
        except Exception as e:
            logger.warning("Failed to delete file '%s': %s", storage_path, e)
            return False

    async def exists(self, storage_path: str) -> bool:
        """Check if file exists in storage."""
        try:
            safe_path = self._resolve_safe_path(storage_path)
            return os.path.exists(safe_path) and os.path.isfile(safe_path)
        except Exception:
            return False
