"""
KrishiMandal — Local file storage service.
Saves uploaded files to disk. Can be swapped for S3 in production.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from src.config import settings


class LocalFileStorage:
    """Store files in the local filesystem under UPLOAD_DIR."""

    def __init__(self):
        self.base_dir = Path(settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_bytes: bytes, farmer_id: str, filename: str) -> str:
        """Save file bytes and return the stored path."""
        ext = Path(filename).suffix or ".bin"
        unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
        farmer_dir = self.base_dir / farmer_id
        farmer_dir.mkdir(parents=True, exist_ok=True)
        file_path = farmer_dir / unique_name
        file_path.write_bytes(file_bytes)
        return str(file_path)

    def get_file_path(self, farmer_id: str, file_id: str) -> str | None:
        """Look up a file by farmer_id and file name."""
        path = self.base_dir / farmer_id / file_id
        return str(path) if path.exists() else None

    def list_files(self, farmer_id: str) -> list[str]:
        """List all files for a farmer."""
        farmer_dir = self.base_dir / farmer_id
        if not farmer_dir.exists():
            return []
        return [f.name for f in farmer_dir.iterdir() if f.is_file()]


# Singleton
_file_storage: LocalFileStorage | None = None


def get_file_storage() -> LocalFileStorage:
    global _file_storage
    if _file_storage is None:
        _file_storage = LocalFileStorage()
    return _file_storage
