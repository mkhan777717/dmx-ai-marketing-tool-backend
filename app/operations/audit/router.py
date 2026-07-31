import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_permission
from app.db.session import get_db_session as get_db
from app.operations.audit.service import AuditLogService

router = APIRouter(prefix="/audit", tags=["Operations - Audit"])


@router.get(
    "/workspace/{workspace_id}",
    dependencies=[Depends(require_permission("workspace", "read"))],
)
async def get_workspace_audit_logs(
    workspace_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve audit logs for a workspace. Accessible only to workspace owners/admins.
    """
    logs = await AuditLogService.get_workspace_audit_logs(
        db, workspace_id, limit, offset
    )
    return logs
