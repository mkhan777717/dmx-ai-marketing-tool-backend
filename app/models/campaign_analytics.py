import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.workspace import Workspace


class CampaignAnalytics(Base, TimestampMixin, TenantMixin):
    __tablename__ = "campaign_analytics"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")
    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="selectin")

    __table_args__ = (Index("ix_campaign_analytics_workspace_id", "workspace_id"),)
