import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.constants.enums import ApiProvider


class SocialAccountConnectRequest(BaseModel):
    provider: ApiProvider
    oauth_code: str
    redirect_uri: Optional[str] = None


class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    provider: ApiProvider
    account_id: str
    name: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
