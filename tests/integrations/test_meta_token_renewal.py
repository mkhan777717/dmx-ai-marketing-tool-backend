import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.events.types.integration import IntegrationTokenExpired
from app.infrastructure.celery.celery_app import celery_app
from app.infrastructure.celery.tasks.integration import meta_token_renewal_task
from app.integrations.connectors.facebook.exceptions import FacebookAuthError
from app.integrations.oauth.models import ConnectionStatus, IntegrationConnection
from app.integrations.oauth.renewal import MetaTokenRenewalService


@pytest.fixture
def mock_secret_service():
    with patch("app.integrations.oauth.renewal.secret_service") as mock_secret:
        mock_secret.decrypt_token.side_effect = lambda t: f"decrypted_{t}" if t else ""
        mock_secret.encrypt_token.side_effect = lambda t: f"encrypted_{t}" if t else ""
        mock_secret.get_provider_credentials.return_value = {
            "client_id": "app_client_123",
            "client_secret": "app_secret_456",
        }
        yield mock_secret


@pytest.fixture
def mock_connection_repo():
    with patch(
        "app.integrations.oauth.renewal.integration_connection_repo"
    ) as mock_repo:

        async def mock_update(db, db_obj, obj_in):
            for k, v in obj_in.items():
                setattr(db_obj, k, v)
            return db_obj

        mock_repo.update.side_effect = mock_update
        yield mock_repo


@pytest.fixture
def mock_sync_engine():
    with patch("app.integrations.oauth.renewal.sync_engine") as mock_sync:
        mock_sync.execute_sync_job = AsyncMock(return_value={"status": "synced"})
        yield mock_sync


@pytest.fixture
def mock_event_publisher():
    with patch("app.integrations.oauth.renewal.EventPublisher") as mock_pub:
        mock_pub.publish = AsyncMock()
        yield mock_pub


# 1. Eligibility Check Tests


def test_eligibility_token_outside_renewal_window():
    now = datetime.now(timezone.utc)
    # Expiration is in 30 days -> Outside 14 day window
    conn = IntegrationConnection(
        id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.CONNECTED,
        access_token="encrypted_token",
        expires_at=now + timedelta(days=30),
    )
    assert MetaTokenRenewalService.is_eligible_for_renewal(conn, now=now) is False


def test_eligibility_freshly_renewed_token_24h_rule():
    now = datetime.now(timezone.utc)
    # Expiration in 59.5 days -> less than 24 hours since issuance
    conn = IntegrationConnection(
        id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.CONNECTED,
        access_token="encrypted_token",
        expires_at=now + timedelta(days=59, hours=12),
    )
    assert MetaTokenRenewalService.is_eligible_for_renewal(conn, now=now) is False


def test_eligibility_eligible_token():
    now = datetime.now(timezone.utc)
    # Expiration in 10 days -> Eligible (within 14 days)
    conn = IntegrationConnection(
        id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.CONNECTED,
        access_token="encrypted_token",
        expires_at=now + timedelta(days=10),
    )
    assert MetaTokenRenewalService.is_eligible_for_renewal(conn, now=now) is True


def test_eligibility_expired_token():
    now = datetime.now(timezone.utc)
    # Already expired 2 days ago
    conn = IntegrationConnection(
        id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.CONNECTED,
        access_token="encrypted_token",
        expires_at=now - timedelta(days=2),
    )
    assert MetaTokenRenewalService.is_eligible_for_renewal(conn, now=now) is False


def test_eligibility_unsupported_provider_or_status():
    now = datetime.now(timezone.utc)
    conn_twitter = IntegrationConnection(
        id=uuid.uuid4(),
        provider="twitter",
        status=ConnectionStatus.CONNECTED,
        access_token="encrypted_token",
        expires_at=now + timedelta(days=5),
    )
    assert (
        MetaTokenRenewalService.is_eligible_for_renewal(conn_twitter, now=now) is False
    )

    conn_disconnected = IntegrationConnection(
        id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.DISCONNECTED,
        access_token="encrypted_token",
        expires_at=now + timedelta(days=5),
    )
    assert (
        MetaTokenRenewalService.is_eligible_for_renewal(conn_disconnected, now=now)
        is False
    )


# 2. Token Renewal Operations


@pytest.mark.asyncio
async def test_facebook_token_renewal_success(
    mock_secret_service, mock_connection_repo, mock_sync_engine
):
    now = datetime.now(timezone.utc)
    conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_old_token",
        expires_at=now + timedelta(days=5),
    )

    new_expires = now + timedelta(days=60)
    renewal_data = {
        "access_token": "new_raw_meta_token_999",
        "refresh_token": None,
        "expires_at": new_expires,
    }

    db_mock = AsyncMock()

    with patch(
        "app.integrations.connectors.facebook.oauth.FacebookOAuthHandler.exchange_for_long_lived_token",
        new_callable=AsyncMock,
    ) as mock_exchange:
        mock_exchange.return_value = renewal_data

        res = await MetaTokenRenewalService.renew_connection(db_mock, conn)

        assert res["status"] == "renewed"
        assert conn.access_token == "encrypted_new_raw_meta_token_999"
        assert conn.expires_at == new_expires
        assert conn.status == ConnectionStatus.CONNECTED

        mock_exchange.assert_called_once_with("decrypted_enc_old_token")
        mock_secret_service.encrypt_token.assert_called_with("new_raw_meta_token_999")
        mock_sync_engine.execute_sync_job.assert_called_once()


@pytest.mark.asyncio
async def test_instagram_token_renewal_success(
    mock_secret_service, mock_connection_repo, mock_sync_engine
):
    now = datetime.now(timezone.utc)
    conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="instagram",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_old_ig_token",
        expires_at=now + timedelta(days=7),
    )

    new_expires = now + timedelta(days=60)
    renewal_data = {
        "access_token": "new_raw_ig_token_777",
        "refresh_token": None,
        "expires_at": new_expires,
    }

    db_mock = AsyncMock()

    with patch(
        "app.integrations.connectors.instagram.oauth.InstagramOAuthHandler.exchange_for_long_lived_token",
        new_callable=AsyncMock,
    ) as mock_exchange:
        mock_exchange.return_value = renewal_data

        res = await MetaTokenRenewalService.renew_connection(db_mock, conn)

        assert res["status"] == "renewed"
        assert conn.access_token == "encrypted_new_raw_ig_token_777"
        assert conn.expires_at == new_expires
        assert conn.status == ConnectionStatus.CONNECTED

        mock_exchange.assert_called_once_with("decrypted_enc_old_ig_token")


@pytest.mark.asyncio
async def test_token_renewal_revoked_token_marks_expired(
    mock_secret_service, mock_connection_repo, mock_event_publisher
):
    now = datetime.now(timezone.utc)
    conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_revoked_token",
        expires_at=now + timedelta(days=3),
    )

    db_mock = AsyncMock()

    with patch(
        "app.integrations.connectors.facebook.oauth.FacebookOAuthHandler.exchange_for_long_lived_token",
        new_callable=AsyncMock,
    ) as mock_exchange:
        mock_exchange.side_effect = FacebookAuthError(
            "Failed to get long-lived token: Session has expired"
        )

        with pytest.raises(FacebookAuthError) as exc_info:
            await MetaTokenRenewalService.renew_connection(db_mock, conn)

        # Connection status set to EXPIRED
        assert conn.status == ConnectionStatus.EXPIRED

        # Verify domain event emitted
        mock_event_publisher.publish.assert_called_once()
        event = mock_event_publisher.publish.call_args[0][0]
        assert isinstance(event, IntegrationTokenExpired)
        assert event.workspace_id == conn.workspace_id
        assert event.provider == "facebook"
        assert event.connection_id == conn.id

        # Verify no token credentials leaked in error message
        assert "enc_revoked_token" not in str(exc_info.value)


# 3. Celery Task and Beat Schedule Tests


def test_celery_task_batch_renewal_handles_individual_failures():
    now = datetime.now(timezone.utc)

    conn1 = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="facebook",
        status=ConnectionStatus.CONNECTED,
        access_token="token1",
        expires_at=now + timedelta(days=5),
    )

    conn2 = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="instagram",
        status=ConnectionStatus.CONNECTED,
        access_token="token2",
        expires_at=now + timedelta(days=6),
    )

    with (
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_all",
            new_callable=AsyncMock,
        ) as mock_get_all,
        patch(
            "app.integrations.oauth.renewal.MetaTokenRenewalService.renew_connection",
            new_callable=AsyncMock,
        ) as mock_renew,
        patch("app.db.session.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_session_cls.return_value.__aenter__.return_value = AsyncMock()
        mock_get_all.return_value = [conn1, conn2]

        # conn1 fails, conn2 succeeds
        mock_renew.side_effect = [
            ValueError("Network error during renewal"),
            {
                "status": "renewed",
                "connection_id": str(conn2.id),
                "provider": "instagram",
            },
        ]

        result = meta_token_renewal_task()

        assert result["processed"] == 2
        assert result["details"][0]["status"] == "failed"
        assert result["details"][1]["status"] == "renewed"


def test_celery_beat_schedule_registered():
    schedule = celery_app.conf.beat_schedule
    assert "meta-token-renewal-daily" in schedule
    assert (
        schedule["meta-token-renewal-daily"]["task"] == "integration.meta_token_renewal"
    )
