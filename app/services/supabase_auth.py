import uuid
from typing import Any

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import settings
from app.models.user import User
from app.repositories.user import user_repo


class SupabaseAuthService:
    @staticmethod
    def verify_jwt(token: str) -> dict[str, Any]:
        """
        Verify Supabase JWT using the project's JWKS endpoint.
        Supports Supabase's current ES256 signing keys.
        """
        try:
            jwks_client = jwt.PyJWKClient(
                f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            )

            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.PyJWKClientError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession, token_payload: dict[str, Any]
    ) -> User:
        """
        Extracts the user from the token payload.
        If the user does not exist locally (first login), creates them automatically.
        """
        supabase_user_id_str = token_payload.get("sub")
        email = token_payload.get("email")

        if not supabase_user_id_str or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing required fields (sub, email)",
            )

        supabase_user_id = uuid.UUID(supabase_user_id_str)

        # Check if user exists by supabase_user_id
        # We need a new repo method or just a custom query.
        # Let's add get_by_supabase_id to repo later, or do it here.
        user = await user_repo.get_by_supabase_id(db, supabase_user_id)

        if not user:
            # First time login sync
            user_data = {
                "supabase_user_id": supabase_user_id,
                "email": email.lower().strip(),
            }
            user = await user_repo.create(db, obj_in=user_data)

        return user
