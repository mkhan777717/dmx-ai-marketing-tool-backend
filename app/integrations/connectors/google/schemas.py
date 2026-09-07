from typing import Optional

from pydantic import BaseModel


class GoogleTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str


class GoogleProfileResponse(BaseModel):
    id: str
    email: str
    verified_email: bool = True
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
