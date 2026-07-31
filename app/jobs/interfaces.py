from abc import ABC, abstractmethod
from typing import Any


class BaseQueueAdapter(ABC):
    """
    Abstract interface for all Queue interactions (Celery, RQ, AWS SQS, etc.).
    """

    @abstractmethod
    async def enqueue(
        self,
        job_name: str,
        payload: dict[str, Any],
        queue: str = "default",
        countdown: int = 0,
    ) -> str:
        """
        Pushes the job to the backend message broker.
        Should return the broker's task ID.
        """
        pass

    @abstractmethod
    async def revoke(self, broker_task_id: str) -> bool:
        """
        Cancels a queued job in the broker.
        """
        pass
