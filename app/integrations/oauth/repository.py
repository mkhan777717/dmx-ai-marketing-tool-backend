import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.oauth.models import IntegrationConnection
from app.repositories.base import BaseRepository


class IntegrationConnectionRepository(BaseRepository[IntegrationConnection]):
    async def get_by_workspace_and_provider(
        self, db: AsyncSession, workspace_id: uuid.UUID, provider: str
    ) -> IntegrationConnection | None:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id, self.model.provider == provider
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_active_connections(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> Sequence[IntegrationConnection]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id, self.model.status == "CONNECTED"
        )
        result = await db.execute(stmt)
        return result.scalars().all()


integration_connection_repo = IntegrationConnectionRepository(IntegrationConnection)
