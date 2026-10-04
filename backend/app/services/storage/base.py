from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseStorageProvider(ABC):
    """
    Abstract storage provider interface.
    Decouples image/file persistence from storage backends (Local, S3, GCS, etc.).
    """

    @abstractmethod
    async def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        subfolder: Optional[str] = None,
        directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save file bytes to storage.
        Returns metadata dict with storage_path, url, filename, file_size_bytes.
        """
        pass

    @abstractmethod
    async def get_file(self, storage_path: str) -> bytes:
        """
        Retrieve raw file bytes from storage.
        """
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage.
        """
        pass

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """
        Check if file exists in storage.
        """
        pass
