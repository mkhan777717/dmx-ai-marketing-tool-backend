from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import ApiProvider
from app.models.base import Base
from app.models.mixins import TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class AIUsage(Base, TimestampMixin, TenantMixin):
    __tablename__ = "ai_usage"

    provider: Mapped[ApiProvider] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)

    generations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")

    __table_args__ = (
        Index("ix_ai_usage_workspace_id", "workspace_id"),
        Index("ix_ai_usage_provider", "provider"),
    )
