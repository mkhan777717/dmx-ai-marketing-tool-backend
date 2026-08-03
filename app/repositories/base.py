import uuid
from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(
        self, db: AsyncSession, id: uuid.UUID, include_deleted: bool = False
    ) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted and hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        include_deleted: bool = False,
    ) -> Sequence[ModelType]:
        stmt = select(self.model)

        if not include_deleted and hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)

        if hasattr(self.model, sort_by):
            order_col = getattr(self.model, sort_by)
            stmt = stmt.order_by(order_col.desc() if sort_desc else order_col.asc())

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        db: AsyncSession,
        filters: dict[str, Any] = None,
        include_deleted: bool = False,
    ) -> int:
        stmt = select(func.count(self.model.id))

        if not include_deleted and hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)

        result = await db.execute(stmt)
        return result.scalar_one()

    async def create(self, db: AsyncSession, *, obj_in: dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: dict[str, Any]
    ) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self, db: AsyncSession, *, id: uuid.UUID, soft: bool = True
    ) -> bool:
        obj = await self.get_by_id(db, id)
        if not obj:
            return False

        if soft and hasattr(obj, "deleted_at"):
            from app.models.base import get_utc_now

            obj.deleted_at = get_utc_now()
            db.add(obj)
            await db.flush()
        else:
            stmt = delete(self.model).where(self.model.id == id)
            await db.execute(stmt)
            await db.flush()
        return True

    async def exists(
        self, db: AsyncSession, id: uuid.UUID, include_deleted: bool = False
    ) -> bool:
        stmt = select(self.model.id).where(self.model.id == id)
        if not include_deleted and hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def bulk_insert(
        self, db: AsyncSession, objects: list[dict[str, Any]]
    ) -> None:
        if not objects:
            return
        stmt = insert(self.model).values(objects)
        await db.execute(stmt)
        await db.flush()

    async def bulk_update(
        self, db: AsyncSession, objects: list[dict[str, Any]]
    ) -> None:
        """
        Expects a list of dictionaries. Each dictionary MUST contain the 'id' of the object to update.
        Uses SQLAlchemy 2.0 bulk update methodology.
        """
        if not objects:
            return
        await db.execute(update(self.model), objects)
        await db.flush()
