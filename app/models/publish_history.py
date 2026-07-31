import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import PublishStatus
from app.models.base import Base
from app.models.mixins import (AuditMixin, SoftDeleteMixin, TenantMixin,
                               TimestampMixin)

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.campaign_content import CampaignContent
    from app.models.social_account import SocialAccount
    from app.models.workspace import Workspace


class PublishHistory(Base, TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "publish_history"

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_content.id", ondelete="CASCADE"), nullable=False
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[PublishStatus] = mapped_column(
        String, default=PublishStatus.PENDING, nullable=False
    )
    external_post_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="selectin")
    content: Mapped["CampaignContent"] = relationship(
        "CampaignContent", lazy="selectin"
    )
    social_account: Mapped["SocialAccount"] = relationship(
        "SocialAccount", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_publish_history_workspace_id", "workspace_id"),
        Index("ix_publish_history_content_id", "content_id"),
        Index("ix_publish_history_status", "status"),
    )
