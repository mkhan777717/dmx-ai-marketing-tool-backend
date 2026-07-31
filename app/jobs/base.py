import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobPayload(BaseModel):
    """
    Base payload structure for all background jobs.
    Tasks should inherit from this to define their specific arguments.
    """

    job_execution_id: Optional[uuid.UUID] = None  # Added when the job is queued

    model_config = ConfigDict(arbitrary_types_allowed=True)
