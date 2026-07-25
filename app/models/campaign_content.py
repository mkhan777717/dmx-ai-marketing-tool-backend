import uuid
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, Table, Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base
from app.models.mixins import TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin
from app.constants.enums import ContentType, ContentStatus

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.models.campaign import Campaign
    from app.models.asset import Asset

content_asset_association = Table(
    "campaign_content_assets",
    Base.metadata,
    Column("content_id", ForeignKey("campaign_content.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
)

class CampaignContent(Base, TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "campaign_content"

    # workspace_id is inherited from TenantMixin
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[ContentType] = mapped_column(String, nullable=False)
    status: Mapped[ContentStatus] = mapped_column(String, default=ContentStatus.DRAFT, nullable=False)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[str | None] = mapped_column(String, nullable=True)
    cta: Mapped[str | None] = mapped_column(String, nullable=True)
    
    seo_title: Mapped[str | None] = mapped_column(String, nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String, nullable=True)
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaign_content.id", ondelete="SET NULL"), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    scheduled_placeholder: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict | list | None] = mapped_column("metadata", JSONB, nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="contents", lazy="selectin")
    
    parent_version: Mapped["CampaignContent"] = relationship("CampaignContent", remote_side="CampaignContent.id", lazy="selectin")
    assets: Mapped[list["Asset"]] = relationship("Asset", secondary=content_asset_association, lazy="selectin")

    __table_args__ = (
        Index("ix_campaign_content_campaign_id", "campaign_id"),
        Index("ix_campaign_content_status", "status"),
        Index("ix_campaign_content_language", "language"),
        Index("ix_campaign_content_content_type", "content_type"),
        Index("ix_campaign_content_version", "version"),
    )
