import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, UniqueConstraint, Enum as SQLEnum, Index
import sqlalchemy as sa
from app.models.base import Base
from app.models.mixins import TimestampMixin, TenantMixin
from app.constants.enums import InviteStatus

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.role import Role
    from app.models.user import User

class WorkspaceInvite(Base, TimestampMixin, TenantMixin):
    __tablename__ = "workspace_invites"

    # workspace_id is inherited from TenantMixin
    
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    inviter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(SQLEnum(InviteStatus), default=InviteStatus.PENDING, index=True, nullable=False)
    
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(index=True, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    role: Mapped["Role"] = relationship("Role", lazy="selectin")
    inviter: Mapped["User"] = relationship("User", foreign_keys=[inviter_id], lazy="selectin")

    __table_args__ = (
        # Partial unique index for active pending invites only (SQLAlchemy partial index)
        Index('uq_workspace_invites_workspace_id_email_pending', 'workspace_id', 'email', unique=True, postgresql_where=sa.text("status = 'PENDING'")),
    )
