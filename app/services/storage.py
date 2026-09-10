import hashlib
import re
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config.settings import settings

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg"}


class StorageService:
    @staticmethod
    def validate_image(file_bytes: bytes, mime_type: str) -> str:
        """
        Validates file size, MIME type, and binary magic bytes for JPEG and PNG images.
        Returns normalized MIME type string.
        """
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file provided.",
            )

        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
            )

        normalized_mime = mime_type.lower().strip()
        if normalized_mime == "image/jpg":
            normalized_mime = "image/jpeg"

        if normalized_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file MIME type '{mime_type}'. Only JPEG and PNG are allowed.",
            )

        # Validate magic header bytes
        is_jpeg = file_bytes.startswith(b"\xff\xd8\xff")
        is_png = file_bytes.startswith(b"\x89PNG\r\n\x1a\n")

        if normalized_mime == "image/jpeg" and not is_jpeg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file header. Content is not a valid JPEG image.",
            )

        if normalized_mime == "image/png" and not is_png:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file header. Content is not a valid PNG image.",
            )

        return normalized_mime

    @classmethod
    async def upload_image(
        cls,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
    ) -> dict[str, Any]:
        """
        Validates and uploads image binary to Supabase Storage.
        Returns a dict containing storage provider, key, public_url, file_size, checksum.
        """
        normalized_mime = cls.validate_image(file_bytes, mime_type)

        # Sanitize filename
        safe_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", original_filename)
        storage_key = f"assets/{uuid.uuid4()}_{safe_filename}"
        checksum = hashlib.sha256(file_bytes).hexdigest()
        file_size = len(file_bytes)

        bucket = settings.SUPABASE_STORAGE_BUCKET
        supabase_url = settings.SUPABASE_URL.rstrip("/")
        service_key = settings.SUPABASE_SERVICE_ROLE_KEY

        if not service_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage configuration missing (SUPABASE_SERVICE_ROLE_KEY).",
            )

        upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{storage_key}"
        headers = {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": normalized_mime,
            "x-upsert": "true",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    upload_url, headers=headers, content=file_bytes
                )
                if response.status_code not in (200, 201):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to upload image to Supabase Storage: {response.text}",
                    )
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Network error while connecting to Supabase Storage: {str(exc)}",
                )

        public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{storage_key}"

        return {
            "storage_provider": "supabase",
            "storage_key": storage_key,
            "public_url": public_url,
            "file_size": file_size,
            "checksum": checksum,
            "mime_type": normalized_mime,
        }
