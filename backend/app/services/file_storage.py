"""File storage service for handling uploads."""

import uuid
from pathlib import Path

import aiofiles

from app.core.config import settings


class FileStorageService:
    """Service for storing and managing uploaded files."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self._ensure_dir_exists()

    def _ensure_dir_exists(self) -> None:
        """Ensure upload directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: uuid.UUID) -> Path:
        """Get project-specific upload directory."""
        project_dir = self.base_dir / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def generate_filename(self, original_filename: str) -> str:
        """Generate unique filename preserving extension."""
        ext = Path(original_filename).suffix.lower()
        unique_id = uuid.uuid4().hex[:12]
        safe_name = Path(original_filename).stem[:50]  # Limit name length
        # Remove special characters
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in safe_name)
        return f"{safe_name}_{unique_id}{ext}"

    async def save_file(
        self,
        project_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> tuple[str, int]:
        """Save file to storage.

        Returns:
            Tuple of (file_path, file_size)
        """
        project_dir = self.get_project_dir(project_id)
        unique_filename = self.generate_filename(filename)
        file_path = project_dir / unique_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return str(file_path), len(content)

    async def read_file(self, file_path: str) -> bytes:
        """Read file from storage."""
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage."""
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False

    def validate_extension(self, filename: str) -> bool:
        """Validate file extension."""
        ext = Path(filename).suffix.lower()
        return ext in settings.ALLOWED_EXTENSIONS

    def validate_size(self, size: int) -> bool:
        """Validate file size."""
        return size <= settings.MAX_UPLOAD_SIZE
