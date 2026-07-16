import uuid
from typing import Any, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from app.repositories.base import BaseRepository
from app.models.asset import Asset
from datetime import datetime, timezone
from app.constants.enums import AssetStatus

class AssetRepository(BaseRepository[Asset]):
    async def get_asset(self, db: AsyncSession, workspace_id: uuid.UUID, asset_id: uuid.UUID) -> Asset | None:
        stmt = select(self.model).where(
            self.model.id == asset_id,
            self.model.workspace_id == workspace_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assets(self, db: AsyncSession, workspace_id: uuid.UUID, limit: int = 100, offset: int = 0) -> Sequence[Asset]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.deleted_at.is_(None)
        ).order_by(desc(self.model.created_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def search_assets(
        self, 
        db: AsyncSession, 
        workspace_id: uuid.UUID,
        asset_type: str | None = None,
        folder: str | None = None,
        uploader_id: uuid.UUID | None = None,
        status: AssetStatus | None = None,
        filename_query: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> Sequence[Asset]:
        conditions = [self.model.workspace_id == workspace_id, self.model.deleted_at.is_(None)]
        
        if asset_type:
            conditions.append(self.model.asset_type == asset_type)
        if folder:
            conditions.append(self.model.folder == folder)
        if uploader_id:
            conditions.append(self.model.uploaded_by == uploader_id)
        if status:
            conditions.append(self.model.status == status)
        if filename_query:
            conditions.append(
                or_(
                    self.model.file_name.ilike(f"%{filename_query}%"),
                    self.model.original_file_name.ilike(f"%{filename_query}%"),
                    self.model.display_name.ilike(f"%{filename_query}%")
                )
            )
            
        stmt = select(self.model).where(and_(*conditions)).order_by(desc(self.model.created_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def soft_delete(self, db: AsyncSession, asset: Asset) -> bool:
        asset.deleted_at = datetime.now(timezone.utc)
        asset.status = AssetStatus.ARCHIVED
        db.add(asset)
        await db.flush()
        return True

    async def restore(self, db: AsyncSession, asset: Asset) -> bool:
        asset.deleted_at = None
        asset.status = AssetStatus.READY
        db.add(asset)
        await db.flush()
        return True

    async def increment_version(self, db: AsyncSession, asset: Asset) -> int:
        asset.version += 1
        db.add(asset)
        await db.flush()
        return asset.version

    async def find_duplicates(self, db: AsyncSession, workspace_id: uuid.UUID, checksum: str) -> Sequence[Asset]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.checksum == checksum,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

asset_repo = AssetRepository(Asset)
