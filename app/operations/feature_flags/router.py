from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session as get_db
from app.operations.feature_flags.service import FeatureFlagService

router = APIRouter(prefix="/feature-flags", tags=["Operations - Feature Flags"])


@router.get("/")
async def get_feature_flags(
    db: AsyncSession = Depends(get_db),
    # _: None = Depends(require_role(["super_admin"]))
):
    """Get all feature flags"""
    flags = await FeatureFlagService.get_all_flags(db)
    return flags
