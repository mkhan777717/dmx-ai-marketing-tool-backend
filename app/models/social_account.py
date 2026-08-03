from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import ApiProvider
from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class SocialAccount(Base, TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "social_accounts"

    provider: Mapped[ApiProvider] = mapped_column(String, nullable=False)
    account_id: Mapped[str] = mapped_column(
        String, nullable=False
    )  # External account ID
    name: Mapped[str] = mapped_column(String, nullable=False)

    access_token: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")

    __table_args__ = (
        Index("ix_social_accounts_workspace_id", "workspace_id"),
        Index("ix_social_accounts_provider", "provider"),
        Index("ix_social_accounts_account_id", "account_id"),
    )
