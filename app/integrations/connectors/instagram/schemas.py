from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class InstagramTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = None


class InstagramProfileResponse(BaseModel):
    id: str
    username: Optional[str] = None
    name: Optional[str] = None
    profile_picture_url: Optional[str] = None


class FacebookPageWithInstagram(BaseModel):
    id: str
    name: str
    access_token: str
    instagram_business_account: Optional[Dict[str, str]] = None


class FacebookPagesResponse(BaseModel):
    data: List[FacebookPageWithInstagram] = Field(default_factory=list)


class InstagramMediaContainerResponse(BaseModel):
    id: str


class InstagramPostPublishResponse(BaseModel):
    id: str
