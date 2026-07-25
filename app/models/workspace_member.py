import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, UniqueConstraint, Enum as SQLEnum
from app.models.base import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin, TenantMixin, AuditMixin
from app.constants.enums import MemberStatus

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.models.role import Role

class WorkspaceMember(Base, TimestampMixin, SoftDeleteMixin, TenantMixin, AuditMixin):
    __tablename__ = "workspace_members"

    # workspace_id is inherited from TenantMixin
    # created_by, updated_by are inherited from AuditMixin
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), index=True, nullable=False)
    
    status: Mapped[MemberStatus] = mapped_column(SQLEnum(MemberStatus), default=MemberStatus.PENDING, index=True, nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_active: Mapped[datetime | None] = mapped_column(nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    role: Mapped["Role"] = relationship("Role", lazy="selectin")
    inviter: Mapped["User"] = relationship("User", foreign_keys=[invited_by], lazy="selectin")

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_id_user_id"),
    )
