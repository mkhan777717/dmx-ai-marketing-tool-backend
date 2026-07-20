import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base
from app.models.mixins import TenantMixin
from app.constants.enums import NotificationType, NotificationPriority

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User

class Notification(Base, TenantMixin):
    __tablename__ = "notifications"

    # workspace_id inherited from TenantMixin
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    
    type: Mapped[NotificationType] = mapped_column(SQLEnum(NotificationType), default=NotificationType.SYSTEM, index=True, nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL, index=True, nullable=False)
    
    data: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    from app.models.mixins import get_utc_now
    created_at: Mapped[datetime] = mapped_column(default=get_utc_now, nullable=False)
    
    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")
