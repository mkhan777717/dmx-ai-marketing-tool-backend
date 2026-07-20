import uuid
from datetime import datetime, timezone
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks, HTTPException, status
from app.models.campaign_schedule import CampaignSchedule
from app.schemas.campaign_schedule import CampaignScheduleCreate, CampaignScheduleUpdate
from app.repositories.campaign_schedule import campaign_schedule_repo
from app.repositories.audit_log import audit_log_repo
from app.constants.enums import ScheduleStatus
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

class CampaignSchedulerService:
    async def schedule_campaign(
        self, db: AsyncSession, campaign_id: uuid.UUID, schedule_data: CampaignScheduleCreate, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> CampaignSchedule:
        if schedule_data.publish_date < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot schedule in the past")

        from sqlalchemy import text
        campaign_state = await db.execute(text("SELECT status FROM campaigns WHERE id = :id AND workspace_id = :ws_id"), {"id": str(campaign_id), "ws_id": str(workspace_id)})
        camp_status = campaign_state.scalar_one_or_none()
        if not camp_status:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        if camp_status in ["COMPLETED", "ARCHIVED"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot schedule a {camp_status} campaign")

        existing = await campaign_schedule_repo.get_by_campaign_id(db, campaign_id, workspace_id)
        
        if existing and existing.status == ScheduleStatus.PUBLISHED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign is already published")
        
        if existing:
            # Update existing
            obj_in = schedule_data.model_dump(exclude_unset=True)
            obj_in["status"] = ScheduleStatus.SCHEDULED
            obj_in["error_message"] = None
            obj_in["updated_by"] = user_id
            updated = await campaign_schedule_repo.update(db, db_obj=existing, obj_in=obj_in)
            
            await self._log_audit(db, workspace_id, user_id, "UPDATE_SCHEDULE", campaign_id, new_values=obj_in)
            return updated
        else:
            # Create new
            obj_in = schedule_data.model_dump()
            obj_in["campaign_id"] = campaign_id
            obj_in["workspace_id"] = workspace_id
            obj_in["created_by"] = user_id
            obj_in["status"] = ScheduleStatus.SCHEDULED
            new_schedule = await campaign_schedule_repo.create(db, obj_in=obj_in)
            
            await self._log_audit(db, workspace_id, user_id, "CREATE_SCHEDULE", campaign_id, new_values=obj_in)
            return new_schedule

    async def publish_immediately(
        self, db: AsyncSession, campaign_id: uuid.UUID, background_tasks: BackgroundTasks, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> CampaignSchedule:
        schedule = await campaign_schedule_repo.get_by_campaign_id(db, campaign_id, workspace_id)
        
        if schedule and schedule.status == ScheduleStatus.PUBLISHED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign is already published")
            
        if not schedule:
            # If no schedule exists, we create a dummy one for the current time
            obj_in = {
                "campaign_id": campaign_id,
                "workspace_id": workspace_id,
                "created_by": user_id,
                "publish_date": datetime.now(timezone.utc),
                "timezone": "UTC",
                "status": ScheduleStatus.SCHEDULED
            }
            schedule = await campaign_schedule_repo.create(db, obj_in=obj_in)
        
        updated = await campaign_schedule_repo.update(db, db_obj=schedule, obj_in={"status": ScheduleStatus.SCHEDULED})
        
        await self._log_audit(db, workspace_id, user_id, "TRIGGER_PUBLISH", campaign_id)
        
        # Fire background task
        background_tasks.add_task(self.execute_publish, db, campaign_id, workspace_id, user_id)
        return updated

    async def pause_schedule(self, db: AsyncSession, campaign_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID) -> CampaignSchedule:
        schedule = await self._get_and_validate_schedule(db, campaign_id, workspace_id)
        if schedule.status != ScheduleStatus.SCHEDULED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only SCHEDULED campaigns can be paused")
            
        updated = await campaign_schedule_repo.update(db, db_obj=schedule, obj_in={"status": ScheduleStatus.PAUSED, "updated_by": user_id})
        await self._log_audit(db, workspace_id, user_id, "PAUSE_SCHEDULE", campaign_id, old_values={"status": ScheduleStatus.SCHEDULED.value}, new_values={"status": ScheduleStatus.PAUSED.value})
        return updated

    async def resume_schedule(self, db: AsyncSession, campaign_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID) -> CampaignSchedule:
        schedule = await self._get_and_validate_schedule(db, campaign_id, workspace_id)
        if schedule.status != ScheduleStatus.PAUSED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PAUSED campaigns can be resumed")
            
        updated = await campaign_schedule_repo.update(db, db_obj=schedule, obj_in={"status": ScheduleStatus.SCHEDULED, "updated_by": user_id})
        await self._log_audit(db, workspace_id, user_id, "RESUME_SCHEDULE", campaign_id, old_values={"status": ScheduleStatus.PAUSED.value}, new_values={"status": ScheduleStatus.SCHEDULED.value})
        return updated

    async def cancel_schedule(self, db: AsyncSession, campaign_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID) -> CampaignSchedule:
        schedule = await self._get_and_validate_schedule(db, campaign_id, workspace_id)
        if schedule.status in [ScheduleStatus.PUBLISHED, ScheduleStatus.CANCELLED]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel a published or already cancelled schedule")
            
        updated = await campaign_schedule_repo.update(db, db_obj=schedule, obj_in={"status": ScheduleStatus.CANCELLED, "updated_by": user_id})
        await self._log_audit(db, workspace_id, user_id, "CANCEL_SCHEDULE", campaign_id, old_values={"status": schedule.status.value}, new_values={"status": ScheduleStatus.CANCELLED.value})
        return updated
        
    async def retry_failed_publishing(
        self, db: AsyncSession, campaign_id: uuid.UUID, background_tasks: BackgroundTasks, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> CampaignSchedule:
        schedule = await self._get_and_validate_schedule(db, campaign_id, workspace_id)
        if schedule.status != ScheduleStatus.FAILED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only FAILED campaigns can be retried")
            
        updated = await campaign_schedule_repo.update(
            db, 
            db_obj=schedule, 
            obj_in={"status": ScheduleStatus.SCHEDULED, "retry_count": schedule.retry_count + 1, "updated_by": user_id}
        )
        
        await self._log_audit(db, workspace_id, user_id, "RETRY_PUBLISH", campaign_id)
        
        background_tasks.add_task(self.execute_publish, db, campaign_id, workspace_id, user_id)
        return updated

    async def execute_publish(self, db: AsyncSession, campaign_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID):
        """
        Background task to execute the actual publishing logic.
        """
        try:
            # Here we would integrate with social media APIs or email providers
            logger.info(f"Executing publish for campaign {campaign_id}...")
            
            # Simulate processing delay and success
            import asyncio
            await asyncio.sleep(2)
            
            schedule = await campaign_schedule_repo.get_by_campaign_id(db, campaign_id, workspace_id)
            if schedule:
                await campaign_schedule_repo.update(db, db_obj=schedule, obj_in={"status": ScheduleStatus.PUBLISHED, "error_message": None})
                await self._log_audit(db, workspace_id, user_id, "PUBLISH_SUCCESS", campaign_id)
                await notification_service.notify_campaign_published(campaign_id, user_id, True)
                
        except Exception as e:
            logger.error(f"Failed to publish campaign {campaign_id}: {str(e)}")
            schedule = await campaign_schedule_repo.get_by_campaign_id(db, campaign_id, workspace_id)
            if schedule:
                await campaign_schedule_repo.update(db, db_obj=schedule, obj_in={"status": ScheduleStatus.FAILED, "error_message": str(e)})
                await self._log_audit(db, workspace_id, user_id, "PUBLISH_FAILED", campaign_id, new_values={"error": str(e)})
                await notification_service.notify_campaign_published(campaign_id, user_id, False, str(e))

    async def get_history(self, db: AsyncSession, campaign_id: uuid.UUID) -> list:
        # Fetch audit logs related to this campaign's schedule
        filters = {
            "resource": "CAMPAIGN_SCHEDULE",
            "resource_id": str(campaign_id)
        }
        logs = await audit_log_repo.get_all(db, filters=filters, sort_by="created_at", sort_desc=True)
        return logs

    async def _get_and_validate_schedule(self, db: AsyncSession, campaign_id: uuid.UUID, workspace_id: uuid.UUID) -> CampaignSchedule:
        schedule = await campaign_schedule_repo.get_by_campaign_id(db, campaign_id, workspace_id)
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign schedule not found")
        return schedule

    async def _log_audit(self, db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, action: str, campaign_id: uuid.UUID, old_values: dict = None, new_values: dict = None):
        # Convert UUID to string for JSON serialization if present
        def sanitize_dict(d: dict):
            if not d: return None
            return {k: str(v) if isinstance(v, uuid.UUID) or isinstance(v, datetime) else v for k, v in d.items()}

        obj_in = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "action": action,
            "resource": "CAMPAIGN_SCHEDULE",
            "resource_id": str(campaign_id),
            "old_values": sanitize_dict(old_values),
            "new_values": sanitize_dict(new_values)
        }
        await audit_log_repo.create(db, obj_in=obj_in)

campaign_scheduler_service = CampaignSchedulerService()
