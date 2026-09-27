import os
import re
import uuid
import shutil
from typing import Tuple, BinaryIO, Union, Any
from src.config.settings import settings


class StorageService:
    """Pluggable Storage Service handling file persistence and public URL resolution."""

    def __init__(self, base_upload_dir: str = settings.UPLOAD_DIR, base_url: str = settings.BASE_URL):
        self.base_upload_dir = os.path.abspath(base_upload_dir)
        self.base_url = base_url.rstrip("/")
        os.makedirs(self.base_upload_dir, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        base = os.path.basename(filename).strip()
        cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
        return cleaned or f"file_{uuid.uuid4().hex[:8]}"

    def generate_storage_key(self, purpose: str, original_filename: str) -> str:
        sanitized = self._sanitize_filename(original_filename)
        unique_prefix = uuid.uuid4().hex
        stored_name = f"{unique_prefix}_{sanitized}"
        purpose_subfolder = re.sub(r"[^a-zA-Z0-9_-]", "", purpose) or "general"
        return os.path.join(purpose_subfolder, stored_name).replace("\\", "/")

    def get_absolute_path(self, relative_path: str) -> str:
        clean_rel = os.path.normpath(relative_path).lstrip(r"\\/")
        abs_path = os.path.abspath(os.path.join(self.base_upload_dir, clean_rel))
        if not abs_path.startswith(self.base_upload_dir):
            raise ValueError("Invalid storage path: attempted path traversal")
        return abs_path

    def get_public_url(self, relative_path: str) -> str:
        clean_rel = relative_path.replace("\\", "/").lstrip("/")
        return f"/static/uploads/{clean_rel}"

    def save_file(
        self,
        file: Any,
        purpose: str,
        original_filename: str,
    ) -> Tuple[str, str, int]:
        rel_path = self.generate_storage_key(purpose, original_filename)
        abs_path = self.get_absolute_path(rel_path)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        underlying_file = getattr(file, "file", file)

        if isinstance(file, (bytes, bytearray)):
            with open(abs_path, "wb") as buffer:
                buffer.write(file)
            size = len(file)
        elif hasattr(underlying_file, "read"):
            if hasattr(underlying_file, "seek"):
                underlying_file.seek(0)
            with open(abs_path, "wb") as buffer:
                shutil.copyfileobj(underlying_file, buffer)
            size = os.path.getsize(abs_path)
        else:
            raise TypeError(f"Unsupported file type for save_file: {type(file)}")

        media_url = self.get_public_url(rel_path)
        return rel_path, media_url, size

    def file_exists(self, relative_path: str) -> bool:
        try:
            abs_path = self.get_absolute_path(relative_path)
            return os.path.isfile(abs_path)
        except (ValueError, TypeError):
            return False

    def get_file_size(self, relative_path: str) -> int:
        try:
            abs_path = self.get_absolute_path(relative_path)
            if os.path.isfile(abs_path):
                return os.path.getsize(abs_path)
        except (ValueError, TypeError):
            pass
        return 0

    def delete_file(self, relative_path: str) -> bool:
        try:
            abs_path = self.get_absolute_path(relative_path)
            if os.path.isfile(abs_path):
                os.remove(abs_path)
                return True
        except Exception:
            pass
        return False
