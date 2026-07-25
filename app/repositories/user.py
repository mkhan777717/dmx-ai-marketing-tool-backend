import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.user import User

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, db: AsyncSession, email: str, include_deleted: bool = False) -> User | None:
        stmt = select(self.model).where(self.model.email == email)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_supabase_id(self, db: AsyncSession, supabase_user_id: uuid.UUID, include_deleted: bool = False) -> User | None:
        stmt = select(self.model).where(self.model.supabase_user_id == supabase_user_id)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

user_repo = UserRepository(User)
