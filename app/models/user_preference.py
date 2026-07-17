import uuid
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    
    theme: Mapped[str] = mapped_column(String, default="system")
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    date_format: Mapped[str] = mapped_column(String, default="YYYY-MM-DD")
    
    notification_preferences: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    ai_preferences: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences", lazy="selectin")
