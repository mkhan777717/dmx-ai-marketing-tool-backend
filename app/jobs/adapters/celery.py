import logging
import uuid
from typing import Any

from app.jobs.interfaces import BaseQueueAdapter

logger = logging.getLogger(__name__)


class CeleryAdapter(BaseQueueAdapter):
    """
    Adapter that interfaces with Celery.
    In a real deployment, this would use `celery_app.send_task(...)`.
    For this mocked validation phase, it safely simulates dispatch to
    avoid hard-crashing if Redis isn't running on the local machine.
    """

    async def enqueue(
        self,
        job_name: str,
        payload: dict[str, Any],
        queue: str = "default",
        countdown: int = 0,
    ) -> str:
        logger.info(
            f"[CeleryAdapter] Mocking enqueue for {job_name} on queue '{queue}' (countdown={countdown})"
        )
        # In production:
        # result = celery_app.send_task(job_name, kwargs=payload, queue=queue, countdown=countdown)
        # return result.id

        return f"celery-task-{uuid.uuid4()}"

    async def revoke(self, broker_task_id: str) -> bool:
        logger.info(f"[CeleryAdapter] Mocking revoke for task {broker_task_id}")
        # In production:
        # celery_app.control.revoke(broker_task_id, terminate=True)
        return True
