import logging

from app.db.session import SessionLocal
from app.events.base import BaseEvent
from app.events.interfaces import BaseEventHandler
from app.operations.audit.service import AuditLogService

logger = logging.getLogger(__name__)


class AuditHandler(BaseEventHandler):
    """
    Listens to business and security events and persists immutable AuditLog records.
    """

    async def handle(self, event: BaseEvent) -> None:
        logger.info(
            f"[AuditHandler] Processing event: {event.event_name} (ID: {event.event_id})"
        )

        # Determine actor and workspace from event context if available
        # The base event typically has workspace_id and user_id if attached by context
        workspace_id = getattr(event, "workspace_id", None)
        actor_id = getattr(event, "user_id", None)

        # Create a DB session specifically for the AuditLog recording
        async with SessionLocal() as db:
            try:
                await AuditLogService.create_audit_log(
                    db=db,
                    action=event.event_name,
                    resource_type="Event",
                    resource_id=event.event_id,
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    new_values=event.model_dump(),
                    metadata_info={"source": "EventSystem"},
                )
                await db.commit()
            except Exception as e:
                logger.error(
                    f"[AuditHandler] Failed to create audit log for event {event.event_name}: {e}"
                )
                await db.rollback()
