from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LinkedInTokenResponse(BaseModel):
    access_token: str
    expires_in: int
    refresh_token: Optional[str] = None
    refresh_token_expires_in: Optional[int] = None
    scope: Optional[str] = None


class LinkedInProfileResponse(BaseModel):
    id: str
    localizedFirstName: Optional[str] = None
    localizedLastName: Optional[str] = None
    profilePicture: Optional[Dict[str, Any]] = None


class LinkedInOrganization(BaseModel):
    organization: str
    role: str
    roleAssignee: str
    state: str


class LinkedInOrganizationsResponse(BaseModel):
    elements: List[LinkedInOrganization] = Field(default_factory=list)


class LinkedInShareContent(BaseModel):
    shareCommentary: Dict[str, str]
    shareMediaCategory: str = "NONE"


class LinkedInPostPayload(BaseModel):
    author: str
    lifecycleState: str = "PUBLISHED"
    specificContent: Dict[str, LinkedInShareContent]
    visibility: Dict[str, str] = {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}


class LinkedInPostResponse(BaseModel):
    id: str
