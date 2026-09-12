import logging
import uuid
from typing import Any

from app.constants.enums import JobPriority
from app.db.session import AsyncSessionLocal
from app.jobs.adapters.celery import CeleryAdapter
from app.jobs.interfaces import BaseQueueAdapter
from app.jobs.serializers import JobSerializer
from app.jobs.services import JobExecutionService

logger = logging.getLogger(__name__)


class QueueService:
    """
    The facade for Business Services and Event Handlers to enqueue background jobs.
    This encapsulates both Database persistence (JobExecution) and the Queue broker.
    """

    def __init__(self, adapter: BaseQueueAdapter):
        self._adapter = adapter

    async def enqueue(
        self,
        job_name: str,
        payload: dict[str, Any],
        queue: str = "default",
        priority: JobPriority = JobPriority.DEFAULT,
        countdown: int = 0,
        max_attempts: int = 3,
    ) -> uuid.UUID:
        serialized_payload = JobSerializer.serialize(payload)

        # 1. Persist the JobExecution record first
        async with AsyncSessionLocal() as db:
            job = await JobExecutionService.create_job(
                db=db,
                job_name=job_name,
                payload=serialized_payload,
                queue=queue,
                priority=priority,
                max_attempts=max_attempts,
            )
            job_id = job.id

            # 2. Inject the ID into the payload so the worker can report back
            serialized_payload["job_execution_id"] = str(job_id)
            job.payload = dict(serialized_payload)

            await db.commit()  # Ensure it's committed before the worker picks it up

        # 3. Send to broker
        try:
            broker_task_id = await self._adapter.enqueue(
                job_name=job_name,
                payload=serialized_payload,
                queue=queue,
                countdown=countdown,
            )
            logger.info(
                f"[QueueService] Job {job_id} ({job_name}) enqueued successfully via {self._adapter.__class__.__name__}. Broker ID: {broker_task_id}"
            )
        except Exception as e:
            logger.error(
                f"[QueueService] Broker failed to enqueue job {job_id}: {str(e)}",
                exc_info=True,
            )
            # Optionally mark the JobExecution as FAILED immediately if broker is down
            async with AsyncSessionLocal() as db:
                await JobExecutionService.mark_failed(
                    db, job_id, error_message=f"Broker failure: {str(e)}"
                )
                await db.commit()

        return job_id


# Global singleton instantiated with the configured adapter
queue_service = QueueService(adapter=CeleryAdapter())
