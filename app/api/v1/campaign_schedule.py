import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.db.models.user import User
from app.db.session import get_db_session as get_db
from app.schemas.campaign_schedule import (
    CampaignScheduleCreate,
    CampaignScheduleResponse,
    CampaignScheduleUpdate,
)
from app.services.campaign_scheduler import campaign_scheduler_service

router = APIRouter(
    prefix="/campaigns/{campaign_id}",
    tags=["campaign-scheduling"],
)


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
        db,
        campaign_id,
        schedule_data,
        workspace_id,
        current_user.id,
    )


@router.put(
    "/schedule",
    response_model=CampaignScheduleResponse,
)
async def update_campaign_schedule(
    campaign_id: uuid.UUID,
    schedule_data: CampaignScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Update a campaign schedule."""
    create_data = CampaignScheduleCreate(
        **schedule_data.model_dump(exclude_unset=True)
    )

    return await campaign_scheduler_service.schedule_campaign(
        db,
        campaign_id,
        create_data,
        workspace_id,
        current_user.id,
    )


@router.delete(
    "/schedule",
    response_model=CampaignScheduleResponse,
)
async def cancel_campaign_schedule(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Cancel a campaign schedule."""
    return await campaign_scheduler_service.cancel_schedule(
        db,
        campaign_id,
        workspace_id,
        current_user.id,
    )


@router.post(
    "/publish",
    response_model=CampaignScheduleResponse,
)
async def publish_campaign_immediately(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Publish a campaign immediately."""
    return await campaign_scheduler_service.publish_immediately(
        db,
        campaign_id,
        background_tasks,
        workspace_id,
        current_user.id,
    )


@router.post(
    "/pause",
    response_model=CampaignScheduleResponse,
)
async def pause_campaign_schedule(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Pause a campaign schedule."""
    return await campaign_scheduler_service.pause_schedule(
        db,
        campaign_id,
        workspace_id,
        current_user.id,
    )


@router.post(
    "/resume",
    response_model=CampaignScheduleResponse,
)
async def resume_campaign_schedule(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Resume a campaign schedule."""
    return await campaign_scheduler_service.resume_schedule(
        db,
        campaign_id,
        workspace_id,
        current_user.id,
    )


@router.get("/history")
async def get_campaign_publishing_history(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
) -> Any:
    """Get campaign scheduling history."""
    return await campaign_scheduler_service.get_history(
        db,
        campaign_id,
    )