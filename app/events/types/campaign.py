import uuid
from typing import Any

from app.events.base import BaseEvent


class CampaignCreated(BaseEvent):
    event_name: str = "CampaignCreated"
    campaign_id: uuid.UUID


class CampaignUpdated(BaseEvent):
    event_name: str = "CampaignUpdated"
    campaign_id: uuid.UUID
    changes: dict[str, Any]


class CampaignDeleted(BaseEvent):
    event_name: str = "CampaignDeleted"
    campaign_id: uuid.UUID


class CampaignPublished(BaseEvent):
    event_name: str = "CampaignPublished"
    campaign_id: uuid.UUID


class CampaignScheduled(BaseEvent):
    event_name: str = "CampaignScheduled"
    campaign_id: uuid.UUID


class CampaignArchived(BaseEvent):
    event_name: str = "CampaignArchived"
    campaign_id: uuid.UUID
