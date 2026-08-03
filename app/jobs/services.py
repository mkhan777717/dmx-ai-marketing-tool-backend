import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import JobPriority, JobStatus
from app.jobs.models import JobExecution
from app.jobs.repositories import job_execution_repo


class JobExecutionService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        job_name: str,
        payload: dict[str, Any],
        queue: str = "default",
        priority: JobPriority = JobPriority.DEFAULT,
        max_attempts: int = 3,
    ) -> JobExecution:
        obj_in = {
            "job_name": job_name,
            "queue": queue,
            "status": JobStatus.QUEUED,
            "priority": priority,
            "payload": payload,
            "max_attempts": max_attempts,
        }
        return await job_execution_repo.create(db, obj_in=obj_in)

    @staticmethod
    async def get_job(db: AsyncSession, job_id: uuid.UUID) -> JobExecution | None:
        return await job_execution_repo.get_by_id(db, id=job_id)

    @staticmethod
    async def mark_started(db: AsyncSession, job_id: uuid.UUID) -> JobExecution | None:
        return await job_execution_repo.mark_started(db, job_id)

    @staticmethod
    async def mark_completed(
        db: AsyncSession, job_id: uuid.UUID, result: dict | None = None
    ) -> JobExecution | None:
        return await job_execution_repo.mark_completed(db, job_id, result)

    @staticmethod
    async def mark_failed(
        db: AsyncSession, job_id: uuid.UUID, error_message: str
    ) -> JobExecution | None:
        return await job_execution_repo.mark_failed(db, job_id, error_message)
