import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, UniqueConstraint
from app.models.base import Base

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=get_utc_now, nullable=False)

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions", lazy="selectin")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_id_permission_id"),
    )
