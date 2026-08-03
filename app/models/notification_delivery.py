import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.notification import Notification
    from app.models.workspace import Workspace


class NotificationDelivery(Base, TimestampMixin, TenantMixin):
    __tablename__ = "notification_deliveries"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g. "IN_APP", "EMAIL"

    status: Mapped[str] = mapped_column(
        String, default="PENDING", nullable=False
    )  # PENDING, SUCCESS, FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    notification: Mapped["Notification"] = relationship("Notification", lazy="selectin")

    __table_args__ = (
        Index("ix_notification_deliveries_notification_id", "notification_id"),
        Index("ix_notification_deliveries_status", "status"),
    )
