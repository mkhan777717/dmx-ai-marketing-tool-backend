import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_permission
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.notification import (NotificationPreferenceResponse,
                                      NotificationResponse)
from app.services.notification import NotificationService

router = APIRouter()


@router.get(
    "",
    response_model=Sequence[NotificationResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("notifications", "read"))],
)
async def list_unread_notifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get unread notifications for the current user.
    """
    return await NotificationService.get_unread(db, current_user.id, limit)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("notifications", "read"))],
)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a specific notification as read.
    """
    notification = await NotificationService.get_by_id(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    return await NotificationService.mark_as_read(db, notification_id)


@router.patch(
    "/read-all",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("notifications", "read"))],
)
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all unread notifications for the user as read.
    """
    count = await NotificationService.mark_all_as_read(db, current_user.id)
    return {"message": f"{count} notifications marked as read"}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("notifications", "manage"))],
)
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a notification.
    """
    notification = await NotificationService.get_by_id(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    await NotificationService.delete(db, notification_id)


@router.get(
    "/preferences",
    response_model=Sequence[NotificationPreferenceResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("notifications", "read"))],
)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get notification preferences for the user.
    """
    return await NotificationService.get_preferences(db, current_user.id)
