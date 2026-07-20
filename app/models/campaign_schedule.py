import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Integer

from app.models.base import Base
from app.models.mixins import TimestampMixin, TenantMixin, AuditMixin
from app.constants.enums import ScheduleStatus

class CampaignSchedule(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "campaign_schedules"

    # workspace_id is inherited from TenantMixin
    
    # Use string reference since campaign.py might not be present in this branch
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    publish_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String, default="UTC", nullable=False)
    
    status: Mapped[ScheduleStatus] = mapped_column(String, default=ScheduleStatus.SCHEDULED, nullable=False)
    
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Note: Relationship is defined using string reference to avoid import issues
    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="selectin", backref="schedule")
