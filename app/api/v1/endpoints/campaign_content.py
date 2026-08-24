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
    CampaignContentUpdate,
)
from app.schemas.responses import ApiResponse
from app.services.ai_content import AIContentService

router = APIRouter()


@router.post(
    "/{workspace_id}/ai/generate",
    response_model=ApiResponse[AIContentGenerateResponse],
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
    response = await AIContentService.generate_content(workspace_id, request)
    return ApiResponse(
        success=True,
        message="AI content generated",
        data=response,
    )


@router.post(
    "/{workspace_id}/campaigns/{campaign_id}/contents",
    response_model=ApiResponse[CampaignContentResponse],
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
    # Always trust the campaign_id from the URL.
    content_in.campaign_id = campaign_id

    try:
        content = await AIContentService.create_campaign_content(
            db,
            workspace_id,
            content_in,
        )

        await db.commit()

        # Refresh after commit so the response reflects persisted DB state.
        await db.refresh(content)

    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        success=True,
        message="Campaign content created",
        data=content,
    )


@router.get(
    "/{workspace_id}/campaigns/{campaign_id}/contents",
    response_model=ApiResponse[Sequence[CampaignContentResponse]],
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
    contents = await AIContentService.get_campaign_contents(
        db,
        workspace_id,
        campaign_id,
        skip,
        limit,
    )

    return ApiResponse(
        success=True,
        message="Campaign contents retrieved",
        data=contents,
    )


@router.get(
    "/{workspace_id}/campaigns/{campaign_id}/contents/{content_id}",
    response_model=ApiResponse[CampaignContentResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("content", "read"))],
)
async def get_campaign_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get a specific campaign content.
    """
    content = await AIContentService.get_content(
        db,
        workspace_id,
        campaign_id,
        content_id,
    )

    return ApiResponse(
        success=True,
        message="Content retrieved",
        data=content,
    )


@router.patch(
    "/{workspace_id}/campaigns/{campaign_id}/contents/{content_id}",
    response_model=ApiResponse[CampaignContentResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("content", "update"))],
)
async def update_campaign_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    content_in: CampaignContentUpdate,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Update existing campaign content.
    """
    try:
        content = await AIContentService.update_content(
            db,
            workspace_id,
            campaign_id,
            content_id,
            content_in,
        )

        await db.commit()

        # Make sure the returned object reflects the committed state.
        await db.refresh(content)

    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        success=True,
        message="Content updated",
        data=content,
    )


@router.delete(
    "/{workspace_id}/campaigns/{campaign_id}/contents/{content_id}",
    response_model=ApiResponse[CampaignContentResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("content", "delete"))],
)
async def delete_campaign_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Delete campaign content.
    """
    try:
        content = await AIContentService.delete_content(
            db,
            workspace_id,
            campaign_id,
            content_id,
        )

        await db.commit()

        if content is not None:
            await db.refresh(content)

    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        success=True,
        message="Content deleted",
        data=content,
    )
