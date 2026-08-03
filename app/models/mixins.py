import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        default=get_utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete support."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )


class TenantMixin:
    """Mixin for workspace isolation (multi-tenancy)."""

    @declared_attr
    def workspace_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            ForeignKey("workspaces.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )


class AuditMixin:
    """Mixin for tracking creator and updater."""

    @declared_attr
    def created_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )

    @declared_attr
    def updated_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )