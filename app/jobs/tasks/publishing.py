import logging
from typing import Any

from app.jobs.base import JobPayload

logger = logging.getLogger(__name__)


class PublishingTaskPayload(JobPayload):
    post_id: str
    platform: str


async def publish_facebook(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to publish a post to Facebook.
    """
    payload = PublishingTaskPayload(**payload_dict)
    logger.info(f"Executing publish_facebook for Post {payload.post_id}")
    return {"status": "success", "post_id": payload.post_id}


async def publish_linkedin(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to publish a post to LinkedIn.
    """
    payload = PublishingTaskPayload(**payload_dict)
    logger.info(f"Executing publish_linkedin for Post {payload.post_id}")
    return {"status": "success", "post_id": payload.post_id}


async def publish_instagram(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to publish a post to Instagram.
    """
    payload = PublishingTaskPayload(**payload_dict)
    logger.info(f"Executing publish_instagram for Post {payload.post_id}")
    return {"status": "success", "post_id": payload.post_id}
