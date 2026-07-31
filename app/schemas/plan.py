import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: str | None = None
    monthly_price: float = Field(0.0, ge=0)
    yearly_price: float = Field(0.0, ge=0)
    max_users: int = Field(1, ge=0)
    max_workspaces: int = Field(1, ge=0)
    max_ai_credits: int = Field(0, ge=0)
    features: dict | list | None = None
    is_active: bool = True


class PlanCreate(PlanBase):
    pass


class PlanUpdate(PlanBase):
    name: str | None = Field(None, max_length=100)
    slug: str | None = Field(None, max_length=100)
    monthly_price: float | None = Field(None, ge=0)
    yearly_price: float | None = Field(None, ge=0)
    max_users: int | None = Field(None, ge=0)
    max_workspaces: int | None = Field(None, ge=0)
    max_ai_credits: int | None = Field(None, ge=0)
    is_active: bool | None = None


class PlanResponse(PlanBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
