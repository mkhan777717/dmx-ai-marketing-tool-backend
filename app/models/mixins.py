from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from sqlalchemy import ForeignKey, Boolean

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=get_utc_now, onupdate=get_utc_now, nullable=False)


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
    """Mixin for organization isolation (multi-tenancy)."""

    @declared_attr
    def organization_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            ForeignKey("organizations.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )

class AuditMixin:
    """Mixin for tracking creator and updater."""
    @declared_attr
    def created_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def updated_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
