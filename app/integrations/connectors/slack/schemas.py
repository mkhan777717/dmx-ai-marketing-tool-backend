from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SlackBotUser(BaseModel):
    bot_user_id: str


class SlackTeam(BaseModel):
    id: str
    name: str


class SlackOAuthResponse(BaseModel):
    ok: bool
    app_id: str
    authed_user: Dict[str, Any]
    scope: str
    token_type: str
    access_token: str
    bot_user_id: str
    team: SlackTeam
    enterprise: Optional[Dict[str, Any]] = None
    is_enterprise_install: bool


class SlackAuthTestResponse(BaseModel):
    ok: bool
    url: str
    team: str
    user: str
    team_id: str
    user_id: str
    bot_id: Optional[str] = None
    is_enterprise_install: bool


class SlackChannel(BaseModel):
    id: str
    name: str
    is_channel: bool
    is_group: bool
    is_im: bool
    created: int
    is_archived: bool
    is_general: bool
    unlinked: int
    name_normalized: str
    is_shared: bool
    is_org_shared: bool
    is_pending_ext_shared: bool
    context_team_id: str
    updated: int
    parent_conversation: Optional[str] = None
    creator: str
    is_ext_shared: bool
    shared_team_ids: List[str] = Field(default_factory=list)
    pending_connected_team_ids: List[str] = Field(default_factory=list)


class SlackConversationsListResponse(BaseModel):
    ok: bool
    channels: List[SlackChannel] = Field(default_factory=list)
    response_metadata: Optional[Dict[str, Any]] = None


class SlackPostMessageResponse(BaseModel):
    ok: bool
    channel: str
    ts: str
    message: Dict[str, Any]
