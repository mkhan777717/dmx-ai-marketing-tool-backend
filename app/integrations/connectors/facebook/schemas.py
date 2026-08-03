from typing import List, Optional

from pydantic import BaseModel, Field


class FacebookTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = None


class FacebookProfileResponse(BaseModel):
    id: str
    name: Optional[str] = None


class FacebookPageInfo(BaseModel):
    id: str
    name: str
    access_token: str
    category: Optional[str] = None
    tasks: List[str] = Field(default_factory=list)


class FacebookPagesResponse(BaseModel):
    data: List[FacebookPageInfo] = Field(default_factory=list)


class FacebookPostResponse(BaseModel):
    id: str
