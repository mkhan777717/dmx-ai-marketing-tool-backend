import pytest
import jwt
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.services.supabase_auth import SupabaseAuthService
from app.core.config.settings import settings

def test_verify_jwt_success():
    payload = {"sub": str(uuid.uuid4()), "email": "test@supabase.com"}
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    
    decoded = SupabaseAuthService.verify_jwt(token)
    assert decoded["email"] == "test@supabase.com"

def test_verify_jwt_expired():
    # PyJWT raises ExpiredSignatureError if 'exp' is in the past
    payload = {"sub": str(uuid.uuid4()), "exp": 0}
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    
    with pytest.raises(HTTPException) as exc:
        SupabaseAuthService.verify_jwt(token)
    assert exc.value.status_code == 401
    assert "expired" in str(exc.value.detail).lower()

@pytest.mark.asyncio
async def test_get_or_create_user_first_login(async_db: AsyncSession):
    sub_id = uuid.uuid4()
    payload = {
        "sub": str(sub_id),
        "email": "newuser@example.com",
        "email_verified": True
    }
    
    user = await SupabaseAuthService.get_or_create_user(async_db, payload)
    assert user.supabase_user_id == sub_id
    assert user.email == "newuser@example.com"
    assert user.is_verified is True
    
    # Second login should return the same user
    user2 = await SupabaseAuthService.get_or_create_user(async_db, payload)
    assert user2.id == user.id
