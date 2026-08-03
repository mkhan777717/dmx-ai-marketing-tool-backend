from datetime import datetime
from typing import Any

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.enums import JobPriority, JobStatus
from app.models.base import Base
from app.models.mixins import TimestampMixin


class JobExecution(Base, TimestampMixin):
    __tablename__ = "job_executions"

    job_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    queue: Mapped[str] = mapped_column(
        String, default="default", index=True, nullable=False
    )

    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus), default=JobStatus.PENDING, index=True, nullable=False
    )
    priority: Mapped[JobPriority] = mapped_column(
        SQLEnum(JobPriority), default=JobPriority.DEFAULT, index=True, nullable=False
    )

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (Index("ix_job_executions_status_queue", "status", "queue"),)
