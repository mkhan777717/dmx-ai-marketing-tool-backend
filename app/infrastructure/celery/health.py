import logging

from app.infrastructure.celery.base_task import BaseTask
from app.infrastructure.celery.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="health.ping")
def ping_task(self) -> str:
    """
    Simple ping task to verify worker execution and queue routing.
    """
    return "pong"


def check_worker_health() -> dict:
    """
    Utility function to inspect the Celery broker status and verify worker availability.
    Intended to be called by an API health endpoint or monitoring script.
    """
    try:
        inspector = celery_app.control.inspect()
        active = inspector.active()

        if active is None:
            return {
                "status": "unavailable",
                "message": "No active Celery workers found.",
            }

        return {
            "status": "healthy",
            "active_workers": list(active.keys()),
            "message": "Celery workers are active and responding.",
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {str(e)}")
        return {"status": "error", "message": str(e)}
