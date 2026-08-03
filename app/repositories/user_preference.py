import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference
from app.repositories.base import BaseRepository


class UserPreferenceRepository(BaseRepository[UserPreference]):
    async def get_by_user_id(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> UserPreference | None:
        stmt = select(self.model).where(self.model.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


user_preference_repo = UserPreferenceRepository(UserPreference)
