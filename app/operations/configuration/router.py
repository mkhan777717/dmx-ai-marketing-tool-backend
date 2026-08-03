from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session as get_db
from app.operations.configuration.service import ConfigurationService

router = APIRouter(prefix="/config", tags=["Operations - Runtime Configuration"])


@router.get("/")
async def get_all_configs(
    db: AsyncSession = Depends(get_db),
    # _: None = Depends(require_role(["super_admin"]))
):
    """Get all runtime configurations."""
    configs = await ConfigurationService.get_all_configs(db)
    return configs
