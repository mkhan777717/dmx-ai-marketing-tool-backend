import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.publisher import EventPublisher
from app.events.types.integration import IntegrationTokenExpired
from app.integrations.connectors.facebook.oauth import FacebookOAuthHandler
from app.integrations.connectors.instagram.oauth import InstagramOAuthHandler
from app.integrations.oauth.models import ConnectionStatus, IntegrationConnection
from app.integrations.oauth.repository import integration_connection_repo
from app.integrations.secrets.service import secret_service
from app.integrations.sync.engine import sync_engine

logger = logging.getLogger(__name__)


class MetaTokenRenewalService:
    RENEWAL_WINDOW_DAYS = 14

    @classmethod
    def is_eligible_for_renewal(
        cls, connection: IntegrationConnection, now: datetime | None = None
    ) -> bool:
        """
        Determines whether a Meta IntegrationConnection is eligible for proactive token renewal.

        Rules:
        1. Provider must be 'facebook' or 'instagram'.
        2. Status must be CONNECTED.
        3. Connection must have an expires_at timestamp and access_token.
        4. Token must not be already expired (expires_at > now).
        5. Token must be within RENEWAL_WINDOW_DAYS (14 days) of expiration (now <= expires_at <= now + 14 days).
        6. At least 24 hours must have elapsed since issuance (expires_at <= now + 59 days).
        """
        if not connection:
            return False

        if connection.provider not in ("facebook", "instagram"):
            return False

        if connection.status != ConnectionStatus.CONNECTED:
            return False

        if not connection.expires_at or not connection.access_token:
            return False

        now_utc = now or datetime.now(timezone.utc)
        expires_at = connection.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        # Skip if already expired
        if expires_at <= now_utc:
            return False

        # Enforce Meta Graph API 24-hour rule: token must be at least 24 hours old.
        # Since long-lived tokens are issued for ~60 days, a freshly renewed token has expires_at ~ (now + 60 days).
        # If expires_at > now + 59 days, less than 24 hours have passed since issuance.
        if expires_at > (now_utc + timedelta(days=59)):
            return False

        # Check if token falls inside the 14-day proactive renewal window
        renewal_cutoff = now_utc + timedelta(days=cls.RENEWAL_WINDOW_DAYS)
        return expires_at <= renewal_cutoff

    @classmethod
    async def renew_connection(
        cls, db: AsyncSession, connection: IntegrationConnection
    ) -> Dict[str, Any]:
        """
        Proactively renews a long-lived Meta User Access Token for a given IntegrationConnection.
        """
        provider = connection.provider.lower()
        if provider not in ("facebook", "instagram"):
            raise ValueError(f"Unsupported provider for Meta token renewal: {provider}")

        if not connection.access_token:
            raise ValueError(
                f"IntegrationConnection {connection.id} has no access_token."
            )

        # 1. Decrypt current token
        try:
            current_token = secret_service.decrypt_token(connection.access_token)
        except Exception as e:
            logger.error(f"Failed to decrypt token for connection {connection.id}")
            raise ValueError("Token decryption failure") from e

        # 2. Fetch provider credentials
        creds = secret_service.get_provider_credentials(provider)
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")

        if not client_id or not client_secret:
            logger.error(f"Missing client credentials for provider {provider}")
            raise ValueError(f"Missing provider credentials for {provider}")

        # 3. Invoke OAuth handler exchange_for_long_lived_token
        if provider == "facebook":
            handler = FacebookOAuthHandler(
                client_id=client_id, client_secret=client_secret
            )
        else:
            handler = InstagramOAuthHandler(
                client_id=client_id, client_secret=client_secret
            )

        try:
            renewed_data = await handler.exchange_for_long_lived_token(current_token)
        except Exception as exc:
            # Handle invalid/revoked/expired token failures per-connection
            logger.warning(
                f"Meta token renewal failed for connection {connection.id} (workspace {connection.workspace_id}). Marking EXPIRED."
            )
            await integration_connection_repo.update(
                db, db_obj=connection, obj_in={"status": ConnectionStatus.EXPIRED}
            )

            # Emit token expired domain event
            await EventPublisher.publish(
                IntegrationTokenExpired(
                    workspace_id=connection.workspace_id,
                    provider=provider,
                    connection_id=connection.id,
                )
            )
            raise exc

        new_access_token = renewed_data.get("access_token")
        new_expires_at = renewed_data.get("expires_at")

        if not new_access_token or not new_expires_at:
            raise ValueError(
                "Meta token renewal response missing access_token or expires_at."
            )

        # 4. Encrypt new token before persistence
        encrypted_token = secret_service.encrypt_token(new_access_token)

        # 5. Transactional database update
        updated_connection = await integration_connection_repo.update(
            db,
            db_obj=connection,
            obj_in={
                "access_token": encrypted_token,
                "expires_at": new_expires_at,
                "status": ConnectionStatus.CONNECTED,
            },
        )

        # 6. Synchronize derived SocialAccount Page Access Tokens
        try:
            await sync_engine.execute_sync_job(
                db,
                payload={
                    "workspace_id": str(connection.workspace_id),
                    "provider": provider,
                    "sync_type": "full",
                },
            )
        except Exception as sync_exc:
            logger.warning(
                f"SocialAccount token re-sync warning after Meta token renewal for workspace {connection.workspace_id}: {sync_exc}"
            )

        return {
            "status": "renewed",
            "connection_id": str(updated_connection.id),
            "provider": provider,
            "new_expires_at": new_expires_at.isoformat(),
        }
