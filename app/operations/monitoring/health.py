from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session as get_db

router = APIRouter(prefix="/health", tags=["Operations - Monitoring"])


@router.get("/live", status_code=status.HTTP_200_OK)
async def health_live():
    """Liveness probe. Indicates if the API server is running."""
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Readiness probe. Checks if the server can accept traffic (tests DB connection)."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return Response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content="Database unavailable",
        )


@router.get("/database", status_code=status.HTTP_200_OK)
async def health_database(db: AsyncSession = Depends(get_db)):
    """Specific database health check."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "connected"}
    except Exception as e:
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=str(e))
