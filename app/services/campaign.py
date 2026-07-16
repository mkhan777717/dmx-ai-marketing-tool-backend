import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.repositories.campaign import campaign_repo
from app.repositories.brand_kit import brand_kit_repo
from app.repositories.asset import asset_repo
from app.repositories.audit_log import audit_log_repo
from app.repositories.notification import notification_repo
from app.constants.enums import CampaignStatus, NotificationType, NotificationPriority

class CampaignService:
    @staticmethod
    def _validate_dates(start_date, end_date):
        if start_date and end_date:
            if start_date > end_date:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be after end date.")
                
    @staticmethod
    async def create_campaign(db: AsyncSession, user: User, workspace: Workspace, data: CampaignCreate) -> Campaign:
        # Validate unique name
        if await campaign_repo.exists_by_name(db, workspace.id, data.campaign_name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A campaign with this name already exists in the workspace.")
            
        CampaignService._validate_dates(data.start_date, data.end_date)
        
        # Verify brand kit belongs to workspace if provided
        if data.brand_kit_id:
            bk = await brand_kit_repo.get_by_workspace(db, workspace.id)
            if not bk or bk.id != data.brand_kit_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Brand Kit does not exist or belong to this workspace.")

        campaign_data = data.model_dump()
        campaign_data["owner_id"] = user.id
        campaign_data["created_by"] = user.id
        campaign_data["updated_by"] = user.id
        campaign_data["status"] = CampaignStatus.DRAFT
        
        campaign = await campaign_repo.create(db, obj_in=campaign_data)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "CREATE_CAMPAIGN",
            "resource": "campaign",
            "resource_id": str(campaign.id),
            "new_values": {"campaign_name": campaign.campaign_name, "status": campaign.status}
        })
        
        return campaign

    @staticmethod
    async def update_campaign(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID, data: CampaignUpdate) -> Campaign:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived campaigns cannot be edited.")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return campaign
            
        # Validate uniqueness if name changing
        if "campaign_name" in update_data and update_data["campaign_name"] != campaign.campaign_name:
            if await campaign_repo.exists_by_name(db, workspace.id, update_data["campaign_name"], exclude_id=campaign.id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A campaign with this name already exists.")
                
        # Validate dates
        start_date = update_data.get("start_date", campaign.start_date)
        end_date = update_data.get("end_date", campaign.end_date)
        CampaignService._validate_dates(start_date, end_date)
        
        # Verify brand kit
        if "brand_kit_id" in update_data and update_data["brand_kit_id"]:
            bk = await brand_kit_repo.get_by_workspace(db, workspace.id)
            if not bk or bk.id != update_data["brand_kit_id"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Brand Kit does not exist or belong to this workspace.")

        update_data["updated_by"] = user.id
        old_values = {k: getattr(campaign, k) for k in update_data.keys() if hasattr(campaign, k)}
        
        updated_campaign = await campaign_repo.update(db, db_obj=campaign, obj_in=update_data)
        
        # Check if status changed to something important to notify
        if "status" in update_data and update_data["status"] != old_values.get("status"):
            await notification_repo.create(db, obj_in={
                "workspace_id": workspace.id,
                "user_id": campaign.owner_id,
                "title": f"Campaign Status Updated",
                "body": f"Campaign '{campaign.campaign_name}' is now {updated_campaign.status}.",
                "type": NotificationType.SYSTEM,
                "priority": NotificationPriority.NORMAL
            })

        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "UPDATE_CAMPAIGN",
            "resource": "campaign",
            "resource_id": str(campaign.id),
            "old_values": old_values,
            "new_values": update_data
        })
        
        return updated_campaign

    @staticmethod
    async def delete_campaign(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID) -> None:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        await campaign_repo.soft_delete(db, campaign)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "DELETE_CAMPAIGN",
            "resource": "campaign",
            "resource_id": str(campaign.id)
        })

    @staticmethod
    async def attach_asset(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID, asset_id: uuid.UUID) -> Campaign:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived campaigns cannot be edited.")
            
        asset = await asset_repo.get_asset(db, workspace.id, asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found or does not belong to this workspace.")
            
        await campaign_repo.add_asset(db, campaign, asset)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "ATTACH_ASSET_TO_CAMPAIGN",
            "resource": "campaign",
            "resource_id": str(campaign.id),
            "new_values": {"asset_id": str(asset.id)}
        })
        
        return campaign

    @staticmethod
    async def detach_asset(db: AsyncSession, user: User, workspace: Workspace, campaign_id: uuid.UUID, asset_id: uuid.UUID) -> Campaign:
        campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        if campaign.status == CampaignStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived campaigns cannot be edited.")
            
        asset = next((a for a in campaign.assets if a.id == asset_id), None)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset is not attached to this campaign.")
            
        await campaign_repo.remove_asset(db, campaign, asset)
        
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "DETACH_ASSET_FROM_CAMPAIGN",
            "resource": "campaign",
            "resource_id": str(campaign.id),
            "new_values": {"asset_id": str(asset.id)}
        })
        
        return campaign

campaign_service = CampaignService()
