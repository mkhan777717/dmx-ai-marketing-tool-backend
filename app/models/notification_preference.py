import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import NotificationType
from app.models.base import Base
from app.models.mixins import TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class NotificationPreference(Base, TimestampMixin, TenantMixin):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[NotificationType] = mapped_column(String, nullable=False)

    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_notification_preferences_user_id", "user_id"),
        Index(
            "ix_notification_preferences_user_type",
            "user_id",
            "notification_type",
            unique=True,
        ),
    )
