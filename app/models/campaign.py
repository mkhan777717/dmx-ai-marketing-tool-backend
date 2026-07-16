import uuid
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, Table, Column, Index
from app.models.base import Base
from app.models.mixins import TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin
from app.constants.enums import CampaignStatus

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.models.brand_kit import BrandKit
    from app.models.asset import Asset
    from app.models.campaign_content import CampaignContent

campaign_asset_association = Table(
    "campaign_assets",
    Base.metadata,
    Column("campaign_id", ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
)

class Campaign(Base, TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "campaigns"

    # workspace_id is inherited from TenantMixin
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    brand_kit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brand_kits.id", ondelete="SET NULL"), nullable=True)
    
    campaign_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(String, nullable=True)
    campaign_type: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Simple comma-separated list of target channels for Phase 4A
    target_channels: Mapped[str | None] = mapped_column(String, nullable=True)
    
    status: Mapped[CampaignStatus] = mapped_column(String, default=CampaignStatus.DRAFT, nullable=False)
    
    budget: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="USD")
    
    start_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin", back_populates="campaigns")
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    brand_kit: Mapped["BrandKit"] = relationship("BrandKit", lazy="selectin")
    
    assets: Mapped[list["Asset"]] = relationship("Asset", secondary=campaign_asset_association, lazy="selectin")
    contents: Mapped[list["CampaignContent"]] = relationship("CampaignContent", back_populates="campaign", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_campaigns_workspace_id", "workspace_id"),
        Index("ix_campaigns_status", "status"),
        Index("ix_campaigns_workspace_name", "workspace_id", "campaign_name", unique=True),
    )
