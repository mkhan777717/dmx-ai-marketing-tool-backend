import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_permission
from app.db.session import get_db_session as get_db
from app.operations.admin.service import AdminOperationsService

router = APIRouter(prefix="/admin", tags=["Operations - Admin Controls"])

# Enforce highest role for all admin ops
admin_dependency = Depends(require_permission("system", "manage"))


@router.get("/jobs", response_model=list[Any])
async def list_jobs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    # _: None = admin_dependency
):
    """List all system jobs."""
    return await AdminOperationsService.get_system_jobs(db, limit, offset)


@router.post("/jobs/{execution_id}/retry")
async def retry_job(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    # _: None = admin_dependency
):
    """Retry a failed or completed job."""
    try:
        job = await AdminOperationsService.retry_job(db, execution_id)
        return {
            "status": "ok",
            "message": "Job re-queued successfully",
            "job_id": job.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{execution_id}/cancel")
async def cancel_job(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    # _: None = admin_dependency
):
    """Cancel a pending/queued job."""
    try:
        job = await AdminOperationsService.cancel_job(db, execution_id)
        return {"status": "ok", "message": "Job cancelled", "job_id": job.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
