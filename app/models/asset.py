import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import AssetStatus, AssetType
from app.models.base import Base
from app.models.mixins import (AuditMixin, SoftDeleteMixin, TenantMixin,
                               TimestampMixin)

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class Asset(Base, TimestampMixin, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "assets"

    # workspace_id is inherited from TenantMixin
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    file_name: Mapped[str] = mapped_column(String, nullable=False)
    original_file_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    asset_type: Mapped[AssetType] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    storage_provider: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    public_url: Mapped[str | None] = mapped_column(String, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)

    checksum: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    folder: Mapped[str | None] = mapped_column(String, nullable=True, default="/")

    tags: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict | list | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    status: Mapped[AssetStatus] = mapped_column(
        String, default=AssetStatus.UPLOADING, nullable=False
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", lazy="selectin", back_populates="assets"
    )
    uploader: Mapped["User"] = relationship(
        "User", foreign_keys=[uploaded_by], lazy="selectin"
    )

    __table_args__ = (
        Index("ix_assets_workspace_id", "workspace_id"),
        Index("ix_assets_asset_type", "asset_type"),
        Index("ix_assets_status", "status"),
        Index("ix_assets_checksum", "checksum"),
        Index("ix_assets_created_at", "created_at"),
    )
