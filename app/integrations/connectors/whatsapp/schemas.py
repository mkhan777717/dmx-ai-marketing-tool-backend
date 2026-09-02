from typing import List, Optional

from pydantic import BaseModel, Field


class WhatsAppTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class WhatsAppPhoneNumber(BaseModel):
    id: str = Field(..., description="Phone Number ID used in Meta Cloud API")
    display_phone_number: str
    verified_name: Optional[str] = None
    code_verification_status: Optional[str] = None
    quality_rating: Optional[str] = None


class WhatsAppPhoneNumbersResponse(BaseModel):
    data: List[WhatsAppPhoneNumber] = Field(default_factory=list)


class WhatsAppBusinessAccount(BaseModel):
    id: str = Field(..., description="WhatsApp Business Account ID (WABA ID)")
    name: Optional[str] = None
    currency: Optional[str] = None
    timezone_id: Optional[str] = None


class WhatsAppAccountsResponse(BaseModel):
    data: List[WhatsAppBusinessAccount] = Field(default_factory=list)
