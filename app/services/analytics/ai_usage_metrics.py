import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_usage import AIUsage


class AIUsageMetricsService:
    @staticmethod
    async def get_metrics(db: AsyncSession, workspace_id: uuid.UUID) -> dict[str, Any]:
        """Calculate aggregated AI usage metrics for a workspace."""
        stmt = select(
            func.sum(AIUsage.generations), func.sum(AIUsage.total_tokens)
        ).where(AIUsage.workspace_id == workspace_id)

        result = (await db.execute(stmt)).first()
        generations = result[0] if result and result[0] else 0
        tokens = result[1] if result and result[1] else 0

        return {
            "total_generations": generations,
            "total_tokens": tokens,
        }
