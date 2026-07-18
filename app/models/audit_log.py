import uuid
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base
from app.models.mixins import TenantMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User

class AuditLog(Base, TenantMixin):
    __tablename__ = "audit_logs"

    # workspace_id inherited from TenantMixin
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    
    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String, index=True, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    
    old_values: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    metadata_info: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True) # avoiding 'metadata' keyword collision in SQLAlchemy
    
    request_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    
    from app.models.mixins import get_utc_now
    from datetime import datetime
    created_at: Mapped[datetime] = mapped_column(default=get_utc_now, nullable=False)
    
    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")
