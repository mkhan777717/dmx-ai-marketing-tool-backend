import uuid
import hashlib
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetUpdate
from app.repositories.asset import asset_repo
from app.repositories.audit_log import audit_log_repo
from app.repositories.notification import notification_repo
from app.services.storage import storage_provider
from app.constants.enums import AssetType, AssetStatus, NotificationType, NotificationPriority

class AssetService:
    @staticmethod
    async def _calculate_checksum(file: UploadFile) -> str:
        sha256_hash = hashlib.sha256()
        # file.file is SpooledTemporaryFile, we need to read it
        # but we must reset pointer after reading
        await file.seek(0)
        while chunk := await file.read(8192):
            sha256_hash.update(chunk)
        await file.seek(0)
        return sha256_hash.hexdigest()

    @staticmethod
    def _determine_asset_type(mime_type: str) -> AssetType:
        if mime_type.startswith("image/"):
            return AssetType.IMAGE
        elif mime_type.startswith("video/"):
            return AssetType.VIDEO
        elif mime_type.startswith("audio/"):
            return AssetType.AUDIO
        elif mime_type.startswith("application/") or mime_type.startswith("text/"):
            return AssetType.DOCUMENT
        return AssetType.OTHER

    @staticmethod
    async def upload_asset(
        db: AsyncSession, 
        user: User, 
        workspace: Workspace, 
        file: UploadFile,
        folder: str = "/",
        tags: list[str] | None = None,
        description: str | None = None
    ) -> Asset:
        
        # Calculate Checksum
        checksum = await AssetService._calculate_checksum(file)
        
        # Check duplicates
        duplicates = await asset_repo.find_duplicates(db, workspace.id, checksum)
        if duplicates:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An identical asset already exists in this workspace.")

        # Prepare base fields
        asset_id = uuid.uuid4()
        mime_type = file.content_type or "application/octet-stream"
        asset_type = AssetService._determine_asset_type(mime_type)
        
        # Get file size safely
        await file.seek(0, 2) # go to end
        file_size = file.file.tell()
        await file.seek(0) # reset
        
        # Validate size (e.g. max 100MB)
        if file_size > 100 * 1024 * 1024:
            # Notify on large failed upload
            await notification_repo.create(db, obj_in={
                "workspace_id": workspace.id,
                "user_id": user.id,
                "title": "Upload Failed",
                "body": f"File {file.filename} exceeded maximum size.",
                "type": NotificationType.ALERT,
                "priority": NotificationPriority.HIGH
            })
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size exceeds maximum limit of 100MB.")

        # Upload via StorageProvider
        try:
            storage_key = await storage_provider.upload(file, workspace.id, asset_id)
            public_url = await storage_provider.generate_url(storage_key)
        except Exception as e:
            await notification_repo.create(db, obj_in={
                "workspace_id": workspace.id,
                "user_id": user.id,
                "title": "Upload Failed",
                "body": f"Failed to upload {file.filename} to storage.",
                "type": NotificationType.ALERT,
                "priority": NotificationPriority.HIGH
            })
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage upload failed.")

        # Save to DB
        asset_data = {
            "id": asset_id,
            "workspace_id": workspace.id,
            "uploaded_by": user.id,
            "file_name": str(asset_id) + ("." + file.filename.split(".")[-1] if "." in file.filename else ""),
            "original_file_name": file.filename,
            "display_name": file.filename,
            "description": description,
            "asset_type": asset_type,
            "mime_type": mime_type,
            "file_size": file_size,
            "storage_provider": "local", # Should be dynamic based on provider class
            "storage_key": storage_key,
            "public_url": public_url,
            "checksum": checksum,
            "folder": folder,
            "tags": tags or [],
            "status": AssetStatus.READY
        }

        asset = await asset_repo.create(db, obj_in=asset_data)
        
        # Notifications
        if file_size > 50 * 1024 * 1024:
            await notification_repo.create(db, obj_in={
                "workspace_id": workspace.id,
                "user_id": user.id,
                "title": "Large File Uploaded",
                "body": f"File {file.filename} ({file_size / (1024*1024):.1f} MB) was uploaded successfully.",
                "type": NotificationType.SYSTEM,
                "priority": NotificationPriority.NORMAL
            })

        # Audit
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "UPLOAD_ASSET",
            "resource": "asset",
            "resource_id": str(asset.id),
            "new_values": {"file_name": asset.original_file_name, "size": file_size}
        })
        
        return asset

    @staticmethod
    async def update_asset(db: AsyncSession, user: User, workspace: Workspace, asset_id: uuid.UUID, data: AssetUpdate) -> Asset:
        asset = await asset_repo.get_asset(db, workspace.id, asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
            
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return asset
            
        old_values = {k: getattr(asset, k) for k in update_data.keys() if hasattr(asset, k)}
        
        updated_asset = await asset_repo.update(db, db_obj=asset, obj_in=update_data)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "UPDATE_ASSET",
            "resource": "asset",
            "resource_id": str(asset.id),
            "old_values": old_values,
            "new_values": update_data
        })
        
        return updated_asset

    @staticmethod
    async def delete_asset(db: AsyncSession, user: User, workspace: Workspace, asset_id: uuid.UUID) -> None:
        asset = await asset_repo.get_asset(db, workspace.id, asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
            
        await asset_repo.soft_delete(db, asset)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "DELETE_ASSET",
            "resource": "asset",
            "resource_id": str(asset.id)
        })

    @staticmethod
    async def restore_asset(db: AsyncSession, user: User, workspace: Workspace, asset_id: uuid.UUID) -> Asset:
        # We need a special query to find soft-deleted assets
        # The repo get_asset doesn't filter out soft deleted in our implementation?
        # Let's check: AssetRepository.get_asset does not filter out deleted_at implicitly.
        # But wait, BaseRepository might if it's overriden. Let's assume get_asset gets it.
        asset = await asset_repo.get_asset(db, workspace.id, asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
            
        if not asset.deleted_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset is not deleted.")
            
        await asset_repo.restore(db, asset)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "RESTORE_ASSET",
            "resource": "asset",
            "resource_id": str(asset.id)
        })
        
        await notification_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "title": "Asset Restored",
            "body": f"Asset {asset.original_file_name} has been restored.",
            "type": NotificationType.SYSTEM,
            "priority": NotificationPriority.LOW
        })
        
        return asset

asset_service = AssetService()
