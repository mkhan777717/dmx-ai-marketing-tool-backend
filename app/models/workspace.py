import uuid
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum as SQLEnum
from app.models.base import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin, AuditMixin
from app.constants.enums import WorkspaceStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.plan import Plan
    from app.models.brand_kit import BrandKit
    from app.models.asset import Asset
    from app.models.campaign import Campaign

class Workspace(Base, TimestampMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    default_language: Mapped[str] = mapped_column(String, default="en")
    
    status: Mapped[WorkspaceStatus] = mapped_column(SQLEnum(WorkspaceStatus), default=WorkspaceStatus.ACTIVE, index=True, nullable=False)
    
    plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    
    # We use post_update=True because User also references Workspace via default_workspace_id
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="owned_workspaces", foreign_keys=[owner_id], lazy="selectin")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="workspaces", lazy="selectin")
    
    brand_kit: Mapped["BrandKit"] = relationship("BrandKit", back_populates="workspace", uselist=False, lazy="selectin", cascade="all, delete-orphan")

    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    # members: Mapped[list["WorkspaceMember"]] = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    # invites: Mapped[list["WorkspaceInvite"]] = relationship("WorkspaceInvite", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    # notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    # audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    # api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
