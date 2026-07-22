from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import Base
from app.models.mixins import TimestampMixin
from app.constants.enums import MembershipStatus, UserRole

if TYPE_CHECKING:
    from .organization import Organization
    from .user import User
    
class Membership(Base, TimestampMixin):
    """
    Represents a user's membership in an organization.
    """

    __tablename__ = "memberships"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_memberships_user_organization",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.MEMBER,
    )

    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_status"),
        nullable=False,
        default=MembershipStatus.ACTIVE,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="memberships",
    )
   