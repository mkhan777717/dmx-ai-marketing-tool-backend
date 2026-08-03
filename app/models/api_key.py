from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.enums import ApiProvider
from app.models.base import Base
from app.models.mixins import TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class ApiKey(Base, TimestampMixin, TenantMixin):
    __tablename__ = "api_keys"

    # workspace_id inherited from TenantMixin
    provider: Mapped[ApiProvider] = mapped_column(
        SQLEnum(ApiProvider),
        index=True,
        nullable=False,
    )

    key_name: Mapped[str] = mapped_column(String, nullable=False)

    encrypted_secret: Mapped[str] = mapped_column(String, nullable=False)

    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        lazy="selectin",
    )