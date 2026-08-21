from celery import Celery
from kombu import Exchange, Queue

from app.config.settings import settings

# Initialize the Celery application
celery_app = Celery(
    "ai_marketing_suite",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery Settings
celery_app.conf.update(
    # General
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Optimization and Prefetching
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # Message Routing
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    # Define custom queues
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("emails", Exchange("emails"), routing_key="emails"),
        Queue("campaigns", Exchange("campaigns"), routing_key="campaigns"),
        Queue("notifications", Exchange("notifications"), routing_key="notifications"),
    ),
    # Task routing maps
    task_routes={
        "app.infrastructure.celery.tasks.emails.*": {"queue": "emails"},
        "app.infrastructure.celery.tasks.campaigns.*": {"queue": "campaigns"},
        "app.infrastructure.celery.tasks.notifications.*": {"queue": "notifications"},
    },
)

# Placeholder for Celery Beat Schedules
celery_app.conf.beat_schedule = {
    # Example Schedule:
    # "cleanup_analytics": {
    #     "task": "app.infrastructure.celery.tasks.cleanup.analytics_cleanup",
    #     "schedule": 86400.0, # 24 hours
    # },
}
# Explicitly import Celery task modules
celery_app.conf.imports = (
    "app.infrastructure.celery.health",
    "app.infrastructure.celery.tasks.integration",
)
