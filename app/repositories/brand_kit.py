import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.repositories.base import BaseRepository
from app.models.brand_kit import BrandKit
from datetime import datetime, timezone

class BrandKitRepository(BaseRepository[BrandKit]):
    async def get_by_workspace(self, db: AsyncSession, workspace_id: uuid.UUID) -> BrandKit | None:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, db: AsyncSession, workspace_id: uuid.UUID) -> bool:
        kit = await self.get_by_workspace(db, workspace_id)
        return kit is not None

    async def update_brand(self, db: AsyncSession, workspace_id: uuid.UUID, obj_in: dict) -> BrandKit | None:
        kit = await self.get_by_workspace(db, workspace_id)
        if not kit:
            return None
        
        for field, value in obj_in.items():
            setattr(kit, field, value)
            
        db.add(kit)
        await db.flush()
        await db.refresh(kit)
        return kit

    async def soft_delete(self, db: AsyncSession, workspace_id: uuid.UUID) -> bool:
        kit = await self.get_by_workspace(db, workspace_id)
        if kit:
            kit.deleted_at = datetime.now(timezone.utc)
            db.add(kit)
            await db.flush()
            return True
        return False

brand_kit_repo = BrandKitRepository(BrandKit)
