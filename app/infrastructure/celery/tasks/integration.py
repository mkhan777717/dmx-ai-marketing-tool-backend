import asyncio
import logging
from typing import Any

from app.db.session import AsyncSessionLocal
from app.infrastructure.celery.base_task import BaseTask
from app.infrastructure.celery.celery_app import celery_app
from app.integrations.sync.engine import sync_engine
from app.jobs.worker import WorkerBase

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="integration.sync")
def integration_sync_task(self, **kwargs: dict[str, Any]) -> Any:
    """
    Celery task wrapper for triggering an integration sync.
    Bridges the synchronous Celery worker with the async WorkerBase and SyncEngine.
    """
    job_execution_id = kwargs.get("job_execution_id")

    if not job_execution_id:
        logger.error(
            "integration.sync task received without job_execution_id in payload."
        )

    async def run_sync() -> Any:
        # Provide a fresh database session for the async task inside the separate worker process
        async with AsyncSessionLocal() as db:
            return await sync_engine.execute_sync_job(db, payload=kwargs)

    # Note: Exceptions raised within run_sync will be caught by WorkerBase and the DB job
    # will be properly managed (e.g. FAILED or RETRYING depending on max_attempts).
    # WorkerBase then re-raises the Exception so Celery can trigger its own retry mechanism.
    return asyncio.run(
        WorkerBase.execute_job(
            execution_id=job_execution_id,
            task_func=run_sync,
        )
    )
