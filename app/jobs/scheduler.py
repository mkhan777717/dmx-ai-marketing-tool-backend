import logging
from typing import Any

from app.constants.enums import JobPriority
from app.jobs.queue import queue_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Abstraction for scheduling recurring jobs.
    In the future, this wraps Celery Beat configuration.
    """

    @staticmethod
    async def schedule_daily(
        job_name: str, payload: dict[str, Any], queue: str = "maintenance"
    ):
        logger.info(f"[SchedulerService] Scheduling daily job: {job_name}")
        # Placeholder for Celery Beat dynamic registration
        pass

    @staticmethod
    async def schedule_cron(
        job_name: str,
        payload: dict[str, Any],
        cron_expression: str,
        queue: str = "maintenance",
    ):
        logger.info(
            f"[SchedulerService] Scheduling cron job ({cron_expression}): {job_name}"
        )
        # Placeholder for Celery Beat cron registration
        pass

    @staticmethod
    async def schedule_at(
        job_name: str,
        payload: dict[str, Any],
        run_at_seconds: int,
        queue: str = "default",
    ):
        """
        Schedule a one-off job in the future.
        """
        logger.info(
            f"[SchedulerService] Scheduling future job in {run_at_seconds}s: {job_name}"
        )
        return await queue_service.enqueue(
            job_name=job_name,
            payload=payload,
            queue=queue,
            countdown=run_at_seconds,
            priority=JobPriority.DEFAULT,
        )
