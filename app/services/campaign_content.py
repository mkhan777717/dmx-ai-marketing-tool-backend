import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.campaign_content import CampaignContent
from app.schemas.campaign_content import CampaignContentCreate, CampaignContentUpdate
from app.repositories.campaign_content import campaign_content_repo
from app.repositories.campaign import campaign_repo
from app.repositories.audit_log import audit_log_repo
from app.repositories.notification import notification_repo
from app.constants.enums import CampaignStatus, ContentStatus, NotificationType, NotificationPriority

class CampaignContentService:
    @staticmethod
    async def create_content(db: AsyncSession, user: User, workspace: Workspace, data: CampaignContentCreate) -> CampaignContent:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, data.campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create content in an archived campaign.")

        content_data = data.model_dump()
        content_data["created_by"] = user.id
        content_data["updated_by"] = user.id
        content_data["version"] = 1
        content_data["is_current"] = True
        
        content = await campaign_content_repo.create(db, obj_in=content_data)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "CREATE_CONTENT",
            "resource": "campaign_content",
            "resource_id": str(content.id),
            "new_values": {"title": content.title, "content_type": content.content_type}
        })
        
        return content

    @staticmethod
    async def update_content(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID, content_id: uuid.UUID, data: CampaignContentUpdate) -> CampaignContent:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign or campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign not found or archived.")
            
        content = await campaign_content_repo.get_current_version(db, workspace.id, campaign_id, content_id)
        if not content:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found or not the current version.")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return content
            
        update_data["updated_by"] = user.id
        old_values = {k: getattr(content, k) for k in update_data.keys() if hasattr(content, k)}
        
        updated_content = await campaign_content_repo.update(db, db_obj=content, obj_in=update_data)
        
        # Notifications for status changes
        if "status" in update_data and update_data["status"] != old_values.get("status"):
            status_map = {
                ContentStatus.IN_REVIEW: "is ready for review",
                ContentStatus.APPROVED: "has been approved",
                ContentStatus.REJECTED: "has been rejected",
                ContentStatus.READY: "is ready for publishing"
            }
            if updated_content.status in status_map:
                await notification_repo.create(db, obj_in={
                    "workspace_id": workspace.id,
                    "user_id": campaign.owner_id,
                    "title": "Content Status Updated",
                    "body": f"Content '{updated_content.title}' {status_map[updated_content.status]}.",
                    "type": NotificationType.SYSTEM,
                    "priority": NotificationPriority.NORMAL
                })
            
            # Audit STATUS_CHANGE specifically if we want
            await audit_log_repo.create(db, obj_in={
                "workspace_id": workspace.id,
                "user_id": user.id,
                "action": "STATUS_CHANGE",
                "resource": "campaign_content",
                "resource_id": str(content.id),
                "old_values": {"status": old_values.get("status")},
                "new_values": {"status": updated_content.status}
            })

        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "UPDATE_CONTENT",
            "resource": "campaign_content",
            "resource_id": str(content.id),
            "old_values": old_values,
            "new_values": update_data
        })
        
        return updated_content

    @staticmethod
    async def delete_content(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID, content_id: uuid.UUID) -> None:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign or campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign not found or archived.")
            
        content = await campaign_content_repo.get_current_version(db, workspace.id, campaign_id, content_id)
        if not content:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found.")
            
        await campaign_content_repo.soft_delete(db, content)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "DELETE_CONTENT",
            "resource": "campaign_content",
            "resource_id": str(content.id)
        })


class CampaignVersionService:
    @staticmethod
    async def create_version(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID, content_id: uuid.UUID) -> CampaignContent:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign or campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign not found or archived.")
            
        content = await campaign_content_repo.get_current_version(db, workspace.id, campaign_id, content_id)
        if not content:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found or not the current version.")
            
        new_version = await campaign_content_repo.create_version(db, content)
        new_version.updated_by = user.id
        db.add(new_version)
        await db.flush()
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "CREATE_VERSION",
            "resource": "campaign_content",
            "resource_id": str(new_version.id),
            "new_values": {"version": new_version.version, "parent": str(new_version.parent_version_id)}
        })
        
        return new_version

    @staticmethod
    async def restore_version(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID, version_id: uuid.UUID) -> CampaignContent:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign or campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign not found or archived.")
            
        restored = await campaign_content_repo.restore_version(db, workspace.id, campaign_id, version_id)
        if not restored:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
            
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "RESTORE_VERSION",
            "resource": "campaign_content",
            "resource_id": str(restored.id),
            "new_values": {"version": restored.version}
        })
        
        return restored

campaign_content_service = CampaignContentService()
campaign_version_service = CampaignVersionService()
