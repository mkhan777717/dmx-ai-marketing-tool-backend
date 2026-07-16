import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.user import User
from app.models.workspace import Workspace
from app.models.brand_kit import BrandKit
from app.schemas.brand_kit import BrandKitCreate, BrandKitUpdate
from app.repositories.brand_kit import brand_kit_repo
from app.repositories.audit_log import audit_log_repo

class BrandKitService:
    @staticmethod
    async def create_brand_kit(db: AsyncSession, user: User, workspace: Workspace, data: BrandKitCreate) -> BrandKit:
        exists = await brand_kit_repo.exists(db, workspace.id)
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace already has a Brand Kit.")
            
        kit_data = data.model_dump()
        kit_data["created_by"] = user.id
        kit_data["updated_by"] = user.id
        
        kit = await brand_kit_repo.create(db, obj_in=kit_data)
        
        # Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "CREATE",
            "resource": "brand_kit",
            "resource_id": str(kit.id),
            "new_values": {"brand_name": kit.brand_name}
        })
        
        return kit

    @staticmethod
    async def get_brand_kit(db: AsyncSession, workspace_id: uuid.UUID) -> BrandKit:
        kit = await brand_kit_repo.get_by_workspace(db, workspace_id)
        if not kit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand Kit not found.")
        return kit

    @staticmethod
    async def update_brand_kit(db: AsyncSession, user: User, workspace: Workspace, data: BrandKitUpdate) -> BrandKit:
        kit = await BrandKitService.get_brand_kit(db, workspace.id)
        
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return kit
            
        update_data["updated_by"] = user.id
        old_values = {k: getattr(kit, k) for k in update_data.keys() if hasattr(kit, k)}
        
        updated_kit = await brand_kit_repo.update_brand(db, workspace.id, update_data)
        
        # Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "UPDATE",
            "resource": "brand_kit",
            "resource_id": str(kit.id),
            "old_values": old_values,
            "new_values": update_data
        })
        
        return updated_kit

    @staticmethod
    async def delete_brand_kit(db: AsyncSession, user: User, workspace: Workspace) -> None:
        kit = await BrandKitService.get_brand_kit(db, workspace.id)
        
        await brand_kit_repo.soft_delete(db, workspace.id)
        
        # Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "DELETE",
            "resource": "brand_kit",
            "resource_id": str(kit.id)
        })

brand_kit_service = BrandKitService()
