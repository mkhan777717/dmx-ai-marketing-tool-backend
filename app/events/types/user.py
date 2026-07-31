import uuid

from app.events.base import BaseEvent


class UserLoggedIn(BaseEvent):
    event_name: str = "UserLoggedIn"
    user_id: uuid.UUID


class UserLoggedOut(BaseEvent):
    event_name: str = "UserLoggedOut"
    user_id: uuid.UUID


class PasswordChanged(BaseEvent):
    event_name: str = "PasswordChanged"
    user_id: uuid.UUID
