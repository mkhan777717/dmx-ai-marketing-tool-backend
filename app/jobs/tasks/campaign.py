import logging
from typing import Any

from app.jobs.base import JobPayload

logger = logging.getLogger(__name__)


class CampaignTaskPayload(JobPayload):
    campaign_id: str
    workspace_id: str


async def publish_campaign(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to publish a campaign.
    """
    payload = CampaignTaskPayload(**payload_dict)
    logger.info(f"Executing publish_campaign for Campaign {payload.campaign_id}")
    # In a real scenario, this would call CampaignService.publish()
    return {"status": "success", "campaign_id": payload.campaign_id}


async def schedule_campaign(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to schedule a campaign.
    """
    payload = CampaignTaskPayload(**payload_dict)
    logger.info(f"Executing schedule_campaign for Campaign {payload.campaign_id}")
    # Call CampaignService.schedule()
    return {"status": "success", "campaign_id": payload.campaign_id}


async def archive_campaign(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to archive a campaign.
    """
    payload = CampaignTaskPayload(**payload_dict)
    logger.info(f"Executing archive_campaign for Campaign {payload.campaign_id}")
    # Call CampaignService.archive()
    return {"status": "success", "campaign_id": payload.campaign_id}
