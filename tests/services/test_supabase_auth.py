import uuid
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.supabase_auth import SupabaseAuthService


# --- ES256 key pair fixture (generated once per test module) ---

_ec_private_key = ec.generate_private_key(ec.SECP256R1())
_ec_public_key = _ec_private_key.public_key()


def _make_mock_jwks_client(public_key):
    """Create a mock PyJWKClient that returns the given public key."""
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key

    mock_client_instance = MagicMock()
    mock_client_instance.get_signing_key_from_jwt.return_value = mock_signing_key

    mock_client_class = MagicMock(return_value=mock_client_instance)
    return mock_client_class


def test_verify_jwt_success():
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "test@supabase.com",
        "aud": "authenticated",
    }
    token = jwt.encode(
        payload, _ec_private_key, algorithm="ES256", headers={"kid": "test-kid"}
    )

    mock_client_class = _make_mock_jwks_client(_ec_public_key)

    with patch("app.services.supabase_auth.jwt.PyJWKClient", mock_client_class):
        decoded = SupabaseAuthService.verify_jwt(token)

    assert decoded["email"] == "test@supabase.com"
    assert decoded["sub"] == payload["sub"]


def test_verify_jwt_expired():
    payload = {
        "sub": str(uuid.uuid4()),
        "exp": 0,
        "aud": "authenticated",
    }
    token = jwt.encode(
        payload, _ec_private_key, algorithm="ES256", headers={"kid": "test-kid"}
    )

    mock_client_class = _make_mock_jwks_client(_ec_public_key)

    with patch("app.services.supabase_auth.jwt.PyJWKClient", mock_client_class):
        with pytest.raises(HTTPException) as exc:
            SupabaseAuthService.verify_jwt(token)

    assert exc.value.status_code == 401
    assert "expired" in str(exc.value.detail).lower()


def test_verify_jwt_jwks_failure():
    """When JWKS endpoint is unreachable or kid is missing, should return 401 not 500."""
    # Create any token — content doesn't matter since JWKS lookup will fail
    payload = {"sub": str(uuid.uuid4()), "aud": "authenticated"}
    token = jwt.encode(
        payload, _ec_private_key, algorithm="ES256", headers={"kid": "unknown-kid"}
    )

    mock_client_instance = MagicMock()
    mock_client_instance.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError(
        "Unable to find a signing key that matches"
    )
    mock_client_class = MagicMock(return_value=mock_client_instance)

    with patch("app.services.supabase_auth.jwt.PyJWKClient", mock_client_class):
        with pytest.raises(HTTPException) as exc:
            SupabaseAuthService.verify_jwt(token)

    assert exc.value.status_code == 401
    assert "invalid" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_get_or_create_user_first_login(async_db: AsyncSession):
    sub_id = uuid.uuid4()
    payload = {
        "sub": str(sub_id),
        "email": "newuser@example.com",
        "email_verified": True,
    }

    user = await SupabaseAuthService.get_or_create_user(async_db, payload)
    assert user.supabase_user_id == sub_id
    assert user.email == "newuser@example.com"

    # Second login should return the same user
    user2 = await SupabaseAuthService.get_or_create_user(async_db, payload)
    assert user2.id == user.id
