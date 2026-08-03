from typing import TYPE_CHECKING

from sqlalchemy import Date, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import SnapshotType
from app.models.base import Base
from app.models.mixins import TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class AnalyticsSnapshot(Base, TimestampMixin, TenantMixin):
    __tablename__ = "analytics_snapshots"

    snapshot_type: Mapped[SnapshotType] = mapped_column(String, nullable=False)
    snapshot_date: Mapped[str] = mapped_column(
        Date, nullable=False
    )  # Will store standard python dates

    campaign_metrics: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    ai_metrics: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    publishing_metrics: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    workspace_metrics: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")

    __table_args__ = (
        Index("ix_analytics_snapshots_workspace_id", "workspace_id"),
        Index(
            "ix_analytics_snapshots_type_date",
            "workspace_id",
            "snapshot_type",
            "snapshot_date",
            unique=True,
        ),
    )
