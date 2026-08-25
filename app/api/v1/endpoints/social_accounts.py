import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_workspace, require_permission
from app.db.session import get_db_session
from app.schemas.social_account import (
    SocialAccountConnectRequest,
    SocialAccountResponse,
)
from app.services.social_account import SocialAccountService

router = APIRouter()


@router.post(
    "/{workspace_id}/social-accounts/connect",
    response_model=SocialAccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("social_accounts", "manage"))],
)
async def connect_social_account(
    workspace_id: uuid.UUID,
    request: SocialAccountConnectRequest,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Connect a new social account via OAuth.
    """
    account = await SocialAccountService.connect_account(db, workspace_id, request)
    await db.commit()
    return account


@router.get(
    "/{workspace_id}/social-accounts",
    response_model=Sequence[SocialAccountResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("social_accounts", "read"))],
)
async def list_social_accounts(
    workspace_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    List all connected social accounts for the workspace.
    """
    return await SocialAccountService.get_accounts(db, workspace_id, skip, limit)
