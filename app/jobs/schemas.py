import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.constants.enums import JobPriority, JobStatus


class JobExecutionResponse(BaseModel):
    id: uuid.UUID
    job_name: str
    queue: str
    status: JobStatus
    priority: JobPriority
    attempts: int
    max_attempts: int
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
