from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import NotificationType
from app.models.base import Base
from app.models.mixins import TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class NotificationTemplate(Base, TimestampMixin, TenantMixin):
    __tablename__ = "notification_templates"

    name: Mapped[str] = mapped_column(String, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(String, nullable=False)

    subject_template: Mapped[str] = mapped_column(String, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")

    __table_args__ = (
        Index("ix_notification_templates_workspace_id", "workspace_id"),
        Index(
            "ix_notification_templates_type",
            "workspace_id",
            "notification_type",
            unique=True,
        ),
    )
