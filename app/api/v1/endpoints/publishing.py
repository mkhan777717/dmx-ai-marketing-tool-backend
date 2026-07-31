import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_workspace, require_permission
from app.db.session import get_db_session
from app.schemas.publishing import PublishHistoryResponse, PublishRequest
from app.services.publishing import PublishingService

router = APIRouter()


@router.post(
    "/{workspace_id}/publishing/publish",
    response_model=PublishHistoryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("content", "publish"))],
)
async def publish_content(
    workspace_id: uuid.UUID,
    request: PublishRequest,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Publish content to a social account.
    """
    return await PublishingService.publish_content(db, workspace_id, request)


@router.get(
    "/{workspace_id}/publishing/history",
    response_model=Sequence[PublishHistoryResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("content", "read"))],
)
async def list_publish_history(
    workspace_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    List publishing history for the workspace.
    """
    return await PublishingService.get_publish_history(db, workspace_id, skip, limit)
