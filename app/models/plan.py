from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace

class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    
    monthly_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    yearly_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    
    max_users: Mapped[int] = mapped_column(Integer, default=1)
    max_workspaces: Mapped[int] = mapped_column(Integer, default=1)
    max_ai_credits: Mapped[int] = mapped_column(Integer, default=0)
    
    features: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    workspaces: Mapped[list["Workspace"]] = relationship("Workspace", back_populates="plan", lazy="selectin")

    __table_args__ = (
        CheckConstraint("monthly_price >= 0", name="ck_plans_monthly_price"),
        CheckConstraint("yearly_price >= 0", name="ck_plans_yearly_price"),
        CheckConstraint("max_users >= 0", name="ck_plans_max_users"),
        CheckConstraint("max_workspaces >= 0", name="ck_plans_max_workspaces"),
        CheckConstraint("max_ai_credits >= 0", name="ck_plans_max_ai_credits"),
    )
