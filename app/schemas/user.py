import uuid
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    supabase_user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    job_title: str | None = None
    language: str = "en"
    two_factor_enabled: bool = False
    onboarding_completed: bool = False
    is_active: bool = True
    is_verified: bool = False
    default_workspace_id: uuid.UUID | None = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    job_title: str | None = None
    language: str | None = None
    two_factor_enabled: bool | None = None
    onboarding_completed: bool | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    default_workspace_id: uuid.UUID | None = None

class UserResponse(UserBase):
    id: uuid.UUID
    last_login: datetime | None = None
    password_changed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
