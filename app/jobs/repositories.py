import uuid
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import JobStatus
from app.jobs.models import JobExecution
from app.models.mixins import get_utc_now
from app.repositories.base import BaseRepository


class JobExecutionRepository(BaseRepository[JobExecution]):
    async def get_by_status(
        self, db: AsyncSession, status: JobStatus, limit: int = 100
    ) -> Sequence[JobExecution]:
        stmt = select(self.model).where(self.model.status == status).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def mark_started(
        self, db: AsyncSession, job_id: uuid.UUID
    ) -> JobExecution | None:
        stmt = (
            update(self.model)
            .where(self.model.id == job_id)
            .values(status=JobStatus.RUNNING, started_at=get_utc_now())
        )
        await db.execute(stmt)
        await db.flush()
        return await self.get_by_id(db, job_id)

    async def mark_completed(
        self, db: AsyncSession, job_id: uuid.UUID, result: dict | None = None
    ) -> JobExecution | None:
        stmt = (
            update(self.model)
            .where(self.model.id == job_id)
            .values(
                status=JobStatus.COMPLETED, completed_at=get_utc_now(), result=result
            )
        )
        await db.execute(stmt)
        await db.flush()
        return await self.get_by_id(db, job_id)

    async def mark_failed(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        error_message: str,
        increment_attempt: bool = True,
    ) -> JobExecution | None:
        job = await self.get_by_id(db, job_id)
        if not job:
            return None

        new_attempts = job.attempts + 1 if increment_attempt else job.attempts
        new_status = (
            JobStatus.FAILED if new_attempts >= job.max_attempts else JobStatus.RETRYING
        )

        stmt = (
            update(self.model)
            .where(self.model.id == job_id)
            .values(
                status=new_status,
                failed_at=get_utc_now() if new_status == JobStatus.FAILED else None,
                error_message=error_message,
                attempts=new_attempts,
            )
        )
        await db.execute(stmt)
        await db.flush()
        return await self.get_by_id(db, job_id)


job_execution_repo = JobExecutionRepository(JobExecution)
