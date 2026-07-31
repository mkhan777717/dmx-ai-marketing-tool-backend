import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
# For dependency injection, assuming similar setup to other routers
# I will simulate the dependency for get_current_user and get_current_workspace
# to fetch user_id and workspace_id. Since the platform provides these, I will import them from where they typically are.
# In case of missing imports in this branch, I'll use placeholders if needed, but standard is:
from app.db.models.user import User
from app.db.session import get_db_session as get_db
from app.schemas.campaign_schedule import (CampaignScheduleCreate,
                                           CampaignScheduleResponse,
                                           CampaignScheduleUpdate)
from app.services.campaign_scheduler import campaign_scheduler_service

router = APIRouter(prefix="/campaigns/{campaign_id}", tags=["campaign-scheduling"])


@router.post(
    "/schedule",
    response_model=CampaignScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def schedule_campaign(
    campaign_id: uuid.UUID,
    schedule_data: CampaignScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Schedule a campaign for publishing."""
    return await campaign_scheduler_service.schedule_campaign(
        db, campaign_id, schedule_data, workspace_id, current_user.id
    )


@router.put("/schedule", response_model=CampaignScheduleResponse)
async def update_campaign_schedule(
    campaign_id: uuid.UUID,
    schedule_data: CampaignScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Update a campaign's schedule."""
    # We can reuse schedule_campaign since it handles both create and update
    # Note: schema difference for update allows partial updates, we cast to create for simplicity
    # but the service should probably handle update explicitly if needed.
    # For now, relying on schedule_campaign to do upsert properly.
    create_data = CampaignScheduleCreate(**schedule_data.model_dump(exclude_unset=True))
    return await campaign_scheduler_service.schedule_campaign(
        db, campaign_id, create_data, workspace_id, current_user.id
    )


@router.delete("/schedule", response_model=CampaignScheduleResponse)
async def cancel_campaign_schedule(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Cancel a campaign schedule."""
    return await campaign_scheduler_service.cancel_schedule(
        db, campaign_id, workspace_id, current_user.id
    )


@router.post("/publish", response_model=CampaignScheduleResponse)
async def publish_campaign_immediately(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Publish a campaign immediately via background task."""
    return await campaign_scheduler_service.publish_immediately(
        db, campaign_id, background_tasks, workspace_id, current_user.id
    )


@router.post("/pause", response_model=CampaignScheduleResponse)
async def pause_campaign_schedule(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Pause a scheduled campaign."""
    return await campaign_scheduler_service.pause_schedule(
        db, campaign_id, workspace_id, current_user.id
    )


@router.post("/resume", response_model=CampaignScheduleResponse)
async def resume_campaign_schedule(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Resume a paused campaign schedule."""
    return await campaign_scheduler_service.resume_schedule(
        db, campaign_id, workspace_id, current_user.id
    )


@router.get("/history")
async def get_campaign_publishing_history(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Get the publishing and scheduling history (Audit Logs) for a campaign."""
    return await campaign_scheduler_service.get_history(db, campaign_id)
