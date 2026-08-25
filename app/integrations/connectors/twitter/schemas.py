from pydantic import BaseModel


class TwitterTokenResponse(BaseModel):
    token_type: str
    expires_in: int
    access_token: str
    scope: str
    refresh_token: str | None = None
