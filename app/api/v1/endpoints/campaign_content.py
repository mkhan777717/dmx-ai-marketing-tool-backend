import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    get_current_user,
    get_current_workspace,
    require_permission,
)
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.campaign_content import (
    AIContentGenerateRequest,
    AIContentGenerateResponse,
    CampaignContentCreate,
    CampaignContentResponse,
)
from app.services.ai_content import AIContentService

router = APIRouter()


@router.post(
    "/{workspace_id}/ai/generate",
    response_model=AIContentGenerateResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("ai", "create"))],
)
async def generate_ai_content(
    workspace_id: uuid.UUID,
    request: AIContentGenerateRequest,
    current_user: User = Depends(get_current_user),
    _=Depends(get_current_workspace),
):
    """
    Generate content using AI providers (e.g., OpenAI, Claude).
    Does not save to DB automatically.
    """
    return await AIContentService.generate_content(workspace_id, request)


@router.post(
    "/{workspace_id}/campaigns/{campaign_id}/contents",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("content", "create"))],
)
async def create_campaign_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_in: CampaignContentCreate,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Save generated or manual content to a campaign.
    """
    # Force the campaign_id from the path
    content_in.campaign_id = campaign_id
    return await AIContentService.create_campaign_content(db, workspace_id, content_in)


@router.get(
    "/{workspace_id}/campaigns/{campaign_id}/contents",
    response_model=Sequence[CampaignContentResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("content", "read"))],
)
async def list_campaign_contents(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    List all content for a specific campaign.
    """
    return await AIContentService.get_campaign_contents(
        db, workspace_id, campaign_id, skip, limit
    )
