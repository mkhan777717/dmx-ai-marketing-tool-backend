from typing import TYPE_CHECKING

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import (AuditMixin, SoftDeleteMixin, TenantMixin,
                               TimestampMixin)

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class BrandKit(Base, TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "brand_kits"

    # workspace_id is inherited from TenantMixin
    brand_name: Mapped[str] = mapped_column(String, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    font_family: Mapped[str | None] = mapped_column(String(100), nullable=True)

    brand_voice: Mapped[str | None] = mapped_column(String, nullable=True)
    tone_of_voice: Mapped[str | None] = mapped_column(String, nullable=True)
    brand_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    website_url: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    ai_writing_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_content_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", lazy="selectin", back_populates="brand_kit"
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_brand_kits_workspace_id"),
    )
