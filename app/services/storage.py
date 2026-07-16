import os
import shutil
import uuid
from abc import ABC, abstractmethod
from typing import Any
from fastapi import UploadFile

class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile, workspace_id: uuid.UUID, asset_id: uuid.UUID) -> str:
        """Uploads a file and returns the storage key."""
        pass

    @abstractmethod
    async def delete(self, storage_key: str) -> bool:
        """Deletes a file by its storage key."""
        pass

    @abstractmethod
    async def generate_url(self, storage_key: str) -> str:
        """Generates a public or signed URL for the asset."""
        pass

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "/tmp/dam_storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def upload(self, file: UploadFile, workspace_id: uuid.UUID, asset_id: uuid.UUID) -> str:
        workspace_dir = os.path.join(self.base_dir, str(workspace_id))
        os.makedirs(workspace_dir, exist_ok=True)
        
        # We will use the asset_id as the primary file name to avoid collisions
        extension = os.path.splitext(file.filename or "")[1]
        storage_key = f"{workspace_id}/{asset_id}{extension}"
        file_path = os.path.join(self.base_dir, storage_key)
        
        # file.file is SpooledTemporaryFile
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return storage_key

    async def delete(self, storage_key: str) -> bool:
        file_path = os.path.join(self.base_dir, storage_key)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    async def generate_url(self, storage_key: str) -> str:
        # In a real local setup, we'd serve this via FastAPI static files.
        # For now, we just return a mock local URL.
        return f"http://localhost:8000/static/uploads/{storage_key}"

storage_provider = LocalStorageProvider()
