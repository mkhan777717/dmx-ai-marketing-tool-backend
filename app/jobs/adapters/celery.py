import logging
from typing import Any

from app.infrastructure.celery.celery_app import celery_app
from app.jobs.interfaces import BaseQueueAdapter

logger = logging.getLogger(__name__)


class CeleryAdapter(BaseQueueAdapter):
    """
    Real Celery adapter responsible for dispatching background jobs
    to the configured Celery broker.
    """

    async def enqueue(
        self,
        job_name: str,
        payload: dict[str, Any],
        queue: str = "default",
        countdown: int = 0,
    ) -> str:
        """
        Enqueue a task into Celery.

        The job_name must match a registered Celery task name,
        e.g. "integration.sync".
        """

        logger.info(
            "[CeleryAdapter] Enqueuing task '%s' " "on queue '%s' (countdown=%s)",
            job_name,
            queue,
            countdown,
        )

        try:
            result = celery_app.send_task(
                job_name,
                kwargs=payload,
                queue=queue,
                countdown=countdown,
            )

            logger.info(
                "[CeleryAdapter] Task '%s' enqueued successfully. "
                "Celery task ID: %s",
                job_name,
                result.id,
            )

            return result.id

        except Exception:
            logger.exception(
                "[CeleryAdapter] Failed to enqueue task '%s'",
                job_name,
            )
            raise

    async def revoke(self, broker_task_id: str) -> bool:
        """
        Revoke a Celery task by its broker task ID.
        """

        logger.info(
            "[CeleryAdapter] Revoking Celery task: %s",
            broker_task_id,
        )

        try:
            celery_app.control.revoke(
                broker_task_id,
                terminate=True,
            )

            return True

        except Exception:
            logger.exception(
                "[CeleryAdapter] Failed to revoke task: %s",
                broker_task_id,
            )
            return False
