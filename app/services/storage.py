import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Optional
from app.config import settings

CHUNK_SIZE = 128 * 1024  # 128 KB chunks for efficient audio streaming

class StorageService(ABC):
    """
    Abstract storage interface.
    Designed so local disk storage can be swapped for S3, Cloudflare R2,
    Supabase Storage, or GCP in Phase 2 without changing application routes.
    """

    @abstractmethod
    def save_file(self, file_bytes: bytes, filename: str, subfolder: str = "music") -> str:
        """Save a file and return its relative access URL or key."""
        pass

    @abstractmethod
    def get_file_path(self, filename: str, subfolder: str = "music") -> Optional[Path]:
        """Return the local path if available, or None for purely remote storage."""
        pass

    @abstractmethod
    def file_exists(self, filename: str, subfolder: str = "music") -> bool:
        """Check if file exists in storage."""
        pass

    @abstractmethod
    def get_file_size(self, filename: str, subfolder: str = "music") -> int:
        """Return file size in bytes."""
        pass

    @abstractmethod
    def get_public_url(self, filename: str, subfolder: str = "music") -> str:
        """Return the public URL path for accessing the file."""
        pass

    @abstractmethod
    def open_stream(
        self, filename: str, subfolder: str = "music", start: int = 0, end: Optional[int] = None
    ) -> Generator[bytes, None, None]:
        """Stream chunks of the file between start and end byte offsets."""
        pass


class LocalStorageService(StorageService):
    """
    Local filesystem implementation of StorageService.
    Safe against directory traversal attacks.
    """

    def __init__(self, music_dir: Optional[Path] = None, cover_dir: Optional[Path] = None):
        self.music_dir = (music_dir or settings.MUSIC_STORAGE_PATH).resolve()
        self.cover_dir = (cover_dir or settings.COVER_STORAGE_PATH).resolve()
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.cover_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, filename: str, subfolder: str) -> Path:
        base_dir = self.cover_dir if subfolder == "covers" else self.music_dir
        # Strip path separators to prevent path traversal
        clean_name = Path(filename).name
        target = (base_dir / clean_name).resolve()
        # Enforce target is strictly within base_dir
        if not str(target).startswith(str(base_dir)):
            raise ValueError(f"Illegal path traversal attempt: {filename}")
        return target

    def save_file(self, file_bytes: bytes, filename: str, subfolder: str = "music") -> str:
        target_path = self._resolve_safe_path(filename, subfolder)
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        return self.get_public_url(target_path.name, subfolder)

    def get_file_path(self, filename: str, subfolder: str = "music") -> Optional[Path]:
        target = self._resolve_safe_path(filename, subfolder)
        return target if target.exists() else None

    def file_exists(self, filename: str, subfolder: str = "music") -> bool:
        target = self._resolve_safe_path(filename, subfolder)
        return target.is_file()

    def get_file_size(self, filename: str, subfolder: str = "music") -> int:
        target = self._resolve_safe_path(filename, subfolder)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {filename}")
        return target.stat().st_size

    def get_public_url(self, filename: str, subfolder: str = "music") -> str:
        clean_name = Path(filename).name
        if subfolder == "covers":
            return f"/media/covers/{clean_name}"
        return f"/media/music/{clean_name}"

    def open_stream(
        self, filename: str, subfolder: str = "music", start: int = 0, end: Optional[int] = None
    ) -> Generator[bytes, None, None]:
        target = self._resolve_safe_path(filename, subfolder)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {filename}")

        file_size = target.stat().st_size
        if end is None or end >= file_size:
            end = file_size - 1

        if start > end:
            return

        with open(target, "rb") as f:
            f.seek(start)
            bytes_remaining = end - start + 1
            while bytes_remaining > 0:
                read_len = min(CHUNK_SIZE, bytes_remaining)
                chunk = f.read(read_len)
                if not chunk:
                    break
                bytes_remaining -= len(chunk)
                yield chunk


# Singleton instance
_storage_instance: Optional[StorageService] = None

def get_storage_service() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND.lower() == "local":
            _storage_instance = LocalStorageService()
        else:
            # Phase 2 extension point (e.g. CloudStorageService)
            _storage_instance = LocalStorageService()
    return _storage_instance
