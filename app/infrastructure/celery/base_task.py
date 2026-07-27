import logging
from celery import Task
import uuid

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """
    Base Celery Task that provides standardized logging, retry behaviors, 
    and robust error handling to keep tasks thin and trackable.
    """
    
    # Standard settings for inherited tasks
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True

    def before_start(self, task_id, args, kwargs):
        """Hook called before the task starts executing."""
        logger.info(f"Task started: {self.name} [ID: {task_id}]")
        super().before_start(task_id, args, kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        """Hook called upon successful execution."""
        logger.info(f"Task succeeded: {self.name} [ID: {task_id}]")
        super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Hook called upon task failure."""
        logger.error(f"Task failed: {self.name} [ID: {task_id}] | Error: {str(exc)}")
        super().on_failure(exc, task_id, args, kwargs, einfo)
