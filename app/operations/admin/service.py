import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import JobStatus
from app.jobs.models import JobExecution
from app.jobs.queue import queue_service


class AdminOperationsService:
    """
    Service for platform administrators to intervene in the system.
    """

    @staticmethod
    async def get_system_jobs(
        db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> Sequence[JobExecution]:
        stmt = (
            select(JobExecution)
            .order_by(JobExecution.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def retry_job(db: AsyncSession, execution_id: uuid.UUID) -> JobExecution:
        # Find the job
        job = await db.get(JobExecution, execution_id)
        if not job:
            raise ValueError("Job not found")

        if job.status not in (JobStatus.FAILED, JobStatus.COMPLETED):
            raise ValueError(f"Job is currently {job.status.value}, cannot retry.")

        # Re-queue
        await queue_service.enqueue(
            job_name=job.job_name,
            payload=job.payload,
            priority=job.priority,
            workspace_id=job.workspace_id,
            user_id=job.user_id,
            queue_name=job.queue_name,
        )
        return job

    @staticmethod
    async def cancel_job(db: AsyncSession, execution_id: uuid.UUID) -> JobExecution:
        job = await db.get(JobExecution, execution_id)
        if not job:
            raise ValueError("Job not found")

        if job.status in (JobStatus.PENDING, JobStatus.QUEUED):
            job.status = JobStatus.FAILED
            job.error_stack = "Cancelled by admin."
            await db.commit()
            await db.refresh(job)
        return job
