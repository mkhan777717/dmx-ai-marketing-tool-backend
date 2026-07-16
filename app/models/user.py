import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey
from app.models.base import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user_preference import UserPreference
    from app.models.workspace import Workspace

class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    supabase_user_id: Mapped[uuid.UUID] = mapped_column(unique=True, index=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    job_title: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, default="en")
    
    default_workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    
    last_login: Mapped[datetime | None] = mapped_column(index=True, nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    preferences: Mapped["UserPreference"] = relationship("UserPreference", back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan")
    
    # Relationships for Phase 2D/2E
    # refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    # sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    # workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    
    owned_workspaces: Mapped[list["Workspace"]] = relationship("Workspace", back_populates="owner", foreign_keys="Workspace.owner_id", lazy="selectin")
    default_workspace: Mapped["Workspace"] = relationship("Workspace", foreign_keys=[default_workspace_id], lazy="selectin", post_update=True)
