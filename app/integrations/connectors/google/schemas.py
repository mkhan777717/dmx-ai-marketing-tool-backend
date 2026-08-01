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
    verified_email: bool
    name: str
    given_name: str
    family_name: str
    picture: str
    locale: str
