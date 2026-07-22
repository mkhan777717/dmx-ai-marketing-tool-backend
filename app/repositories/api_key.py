import uuid
import base64
from app import db
from cryptography.fernet import Fernet
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.api_key import ApiKey
from app.core.config.settings import settings

class ApiKeyRepository(BaseRepository[ApiKey]):
    def __init__(self, model: type[ApiKey]):
        super().__init__(model)
        # We need a 32 url-safe base64-encoded byte string for Fernet
        key = settings.ENCRYPTION_KEY
        if len(key) != 44:
            # Fallback for dev if not configured properly, in prod it should crash explicitly
            key = base64.urlsafe_b64encode(b'0' * 32).decode('utf-8')
        self.fernet = Fernet(key.encode('utf-8'))

    def encrypt_secret(self, secret: str) -> str:
        return self.fernet.encrypt(secret.encode('utf-8')).decode('utf-8')

    def decrypt_secret(self, encrypted_secret: str) -> str:
        return self.fernet.decrypt(encrypted_secret.encode('utf-8')).decode('utf-8')

    async def create_api_key(self, db: AsyncSession, obj_in: dict) -> ApiKey:
        secret = obj_in.pop("secret")
        obj_in["encrypted_secret"] = self.encrypt_secret(secret)
        
        api_key = self.model(**obj_in)
        db.add(api_key)
        await db.flush()
        await db.refresh(api_key)
        return api_key

    async def get_active_by_organization(
    self,
    db: AsyncSession,
    organization_id: uuid.UUID, 
    ) -> Sequence[ApiKey]:
        stmt = (
            select(self.model)
            .where(
            self.model.organization_id == organization_id,
            self.model.is_active.is_(True),
        )
    )

        result = await db.execute(stmt)
        return result.scalars().all()

api_key_repo = ApiKeyRepository(ApiKey)
