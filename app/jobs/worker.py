import logging
import uuid
from typing import Any, Awaitable, Callable

from app.db.session import AsyncSessionLocal
from app.jobs.exceptions import JobExecutionError
from app.jobs.services import JobExecutionService

logger = logging.getLogger(__name__)


class WorkerBase:
    """
    Standardizes how background workers execute tasks.
    It manages the JobExecution state transitions (RUNNING -> COMPLETED/FAILED)
    in the database, completely isolating this from the Celery worker function.
    """

    @staticmethod
    async def execute_job(
        execution_id: str, task_func: Callable[..., Awaitable[Any]], **kwargs
    ):
        """
        Executes a job securely, updating the DB states.
        """
        if not execution_id:
            logger.error(
                "Job received without execution_id. Executing without tracking."
            )
            return await task_func(**kwargs)

        try:
            job_id = uuid.UUID(execution_id)
        except ValueError:
            logger.error(f"Invalid execution_id format: {execution_id}")
            return await task_func(**kwargs)

        async with AsyncSessionLocal() as db:
            # 1. Mark as running
            job = await JobExecutionService.mark_started(db, job_id)
            if not job:
                logger.error(f"Job {job_id} not found in DB before execution.")
                # We could choose to abort, but let's try running anyway
                return await task_func(**kwargs)
            await db.commit()

            # 2. Execute
            try:
                logger.info(f"Executing Job {job_id} ({job.job_name})")
                result = await task_func(**kwargs)

                # 3. Mark completed
                await JobExecutionService.mark_completed(
                    db, job_id, result={"result": "success", "data": result}
                )
                await db.commit()
                logger.info(f"Job {job_id} completed successfully.")
                return result

            except Exception as e:
                # 4. Mark failed
                logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
                await JobExecutionService.mark_failed(db, job_id, error_message=str(e))
                await db.commit()
                raise JobExecutionError(f"Task failed: {str(e)}") from e
