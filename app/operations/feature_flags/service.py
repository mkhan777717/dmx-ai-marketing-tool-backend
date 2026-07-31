import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.operations.feature_flags.models import FeatureFlag, WorkspaceFeature


class FeatureFlagService:
    @staticmethod
    async def is_enabled(
        db: AsyncSession, flag_key: str, workspace_id: uuid.UUID | None = None
    ) -> bool:
        """
        Evaluate if a feature is enabled.
        Checks workspace override first, then falls back to global flag.
        """
        if workspace_id:
            stmt = select(WorkspaceFeature).where(
                WorkspaceFeature.flag_key == flag_key,
                WorkspaceFeature.workspace_id == workspace_id,
            )
            result = await db.execute(stmt)
            ws_flag = result.scalars().first()
            if ws_flag:
                return ws_flag.is_enabled

        stmt = select(FeatureFlag).where(FeatureFlag.key == flag_key)
        result = await db.execute(stmt)
        global_flag = result.scalars().first()

        return global_flag.is_enabled if global_flag else False

    @staticmethod
    async def get_all_flags(db: AsyncSession) -> Sequence[FeatureFlag]:
        result = await db.execute(select(FeatureFlag))
        return result.scalars().all()
