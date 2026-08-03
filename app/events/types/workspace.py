import uuid

from app.events.base import BaseEvent


class WorkspaceCreated(BaseEvent):
    event_name: str = "WorkspaceCreated"


class WorkspaceUpdated(BaseEvent):
    event_name: str = "WorkspaceUpdated"


class WorkspaceDeleted(BaseEvent):
    event_name: str = "WorkspaceDeleted"


class MemberInvited(BaseEvent):
    event_name: str = "MemberInvited"
    invited_email: str
    role_id: uuid.UUID


class MemberJoined(BaseEvent):
    event_name: str = "MemberJoined"
    user_id: uuid.UUID


class RoleChanged(BaseEvent):
    event_name: str = "RoleChanged"
    user_id: uuid.UUID
    new_role_id: uuid.UUID
