import logging
import uuid
from datetime import timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.circuit_breaker.breaker import get_circuit_breaker
from app.integrations.exceptions import IntegrationError
from app.integrations.oauth.models import ConnectionStatus, IntegrationConnection
from app.integrations.oauth.repository import integration_connection_repo
from app.integrations.registry import ConnectorFactory
from app.integrations.retry.policy import retry_policy
from app.integrations.secrets.service import secret_service

logger = logging.getLogger(__name__)


class IntegrationService:
    @staticmethod
    async def get_connection(
        db: AsyncSession, workspace_id: uuid.UUID, provider: str
    ) -> IntegrationConnection | None:
        return await integration_connection_repo.get_by_workspace_and_provider(
            db, workspace_id, provider
        )

    @staticmethod
    async def list_connections(
        db: AsyncSession, workspace_id: uuid.UUID
    ) -> list[IntegrationConnection]:
        return await integration_connection_repo.get_active_connections(
            db, workspace_id
        )

    @staticmethod
    async def connect_provider(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        provider: str,
        auth_code: str,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
    ) -> IntegrationConnection:
        import hashlib

        provider = provider.lower()
        credentials = secret_service.get_provider_credentials(provider)

        # Instantiate Connector
        connector = ConnectorFactory.create(provider, credentials)

        # Retrieve circuit breaker
        breaker = get_circuit_breaker(provider)

        code_fp = (
            hashlib.sha256(auth_code.encode()).hexdigest()[:10] if auth_code else "none"
        )
        logger.info(
            f"[IntegrationService] Exchanging single-use auth_code: provider={provider}, workspace_id={workspace_id}, code_fp={code_fp}, redirect_uri={redirect_uri}"
        )

        try:
            # OAuth authorization codes are single-use tokens by definition (RFC 6749 Section 4.1.2).
            # Execute code exchange through circuit breaker without retrying single-use codes,
            # ensuring one authorization code is exchanged exactly once.
            connect_kwargs: dict[str, Any] = {}
            if code_verifier:
                connect_kwargs["code_verifier"] = code_verifier
            if redirect_uri:
                connect_kwargs["redirect_uri"] = redirect_uri

            metadata = await breaker.call(
                connector.connect, auth_code, **connect_kwargs
            )
            access_token = metadata.pop("access_token", None)
            refresh_token = metadata.pop("refresh_token", None)
            expires_at = metadata.pop("expires_at", None)

            # DB column is TIMESTAMP WITHOUT TIME ZONE.
            # Store UTC as a naive datetime.
            if expires_at is not None and expires_at.tzinfo is not None:
                expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)

            # Encrypt tokens
            enc_access = (
                secret_service.encrypt_token(access_token) if access_token else None
            )
            enc_refresh = (
                secret_service.encrypt_token(refresh_token) if refresh_token else None
            )

            # Save Connection
            existing = await integration_connection_repo.get_by_workspace_and_provider(
                db, workspace_id, provider
            )
            if existing:
                conn_result = await integration_connection_repo.update(
                    db,
                    db_obj=existing,
                    obj_in={
                        "status": ConnectionStatus.CONNECTED,
                        "access_token": enc_access,
                        "refresh_token": enc_refresh,
                        "expires_at": expires_at,
                        "metadata_info": metadata,
                    },
                )
            else:
                conn_result = await integration_connection_repo.create(
                    db,
                    obj_in={
                        "workspace_id": workspace_id,
                        "provider": provider,
                        "status": ConnectionStatus.CONNECTED,
                        "access_token": enc_access,
                        "refresh_token": enc_refresh,
                        "expires_at": expires_at,
                        "metadata_info": metadata,
                    },
                )

            # Instantly persist SocialAccount for single-account providers like LinkedIn
            if provider == "linkedin" and metadata and metadata.get("author_urn"):
                author_urn = metadata["author_urn"]
                profile_name = metadata.get("profile_name") or "LinkedIn Member"
                from app.constants.enums import ApiProvider
                from app.repositories.social_account import social_account_repo

                existing_accs = await social_account_repo.get_all(
                    db,
                    filters={
                        "workspace_id": workspace_id,
                        "provider": ApiProvider.LINKEDIN,
                        "account_id": author_urn,
                    },
                )
                if existing_accs:
                    await social_account_repo.update(
                        db,
                        db_obj=existing_accs[0],
                        obj_in={
                            "name": profile_name,
                            "access_token": enc_access,
                            "refresh_token": enc_refresh,
                            "expires_at": expires_at,
                            "is_active": True,
                        },
                    )
                else:
                    await social_account_repo.create(
                        db,
                        obj_in={
                            "workspace_id": workspace_id,
                            "provider": ApiProvider.LINKEDIN,
                            "account_id": author_urn,
                            "name": profile_name,
                            "access_token": enc_access,
                            "refresh_token": enc_refresh,
                            "expires_at": expires_at,
                            "is_active": True,
                        },
                    )

            return conn_result

        except IntegrationError as e:
            logger.error(f"Integration error connecting to {provider}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error connecting to {provider}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to provider",
            )

    @staticmethod
    async def disconnect_provider(
        db: AsyncSession, workspace_id: uuid.UUID, provider: str
    ) -> bool:
        provider = provider.lower()
        connection = await integration_connection_repo.get_by_workspace_and_provider(
            db, workspace_id, provider
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
            )

        credentials = secret_service.get_provider_credentials(provider)
        decrypted_token = secret_service.decrypt_token(connection.access_token)
        connector = ConnectorFactory.create(
            provider, credentials, access_token=decrypted_token
        )

        breaker = get_circuit_breaker(provider)

        try:

            @retry_policy(max_retries=2)
            async def _disconnect():
                return await breaker.call(connector.disconnect)

            await _disconnect()
        except Exception as e:
            logger.warning(
                f"Provider {provider} disconnect failed on remote side, but will clean up locally. Error: {str(e)}"
            )

        await integration_connection_repo.update(
            db,
            db_obj=connection,
            obj_in={
                "status": ConnectionStatus.DISCONNECTED,
                "access_token": None,
                "refresh_token": None,
                "expires_at": None,
            },
        )

        return True

    @staticmethod
    async def get_connector_instance(connection: IntegrationConnection) -> Any:
        provider = connection.provider.lower()
        credentials = secret_service.get_provider_credentials(provider)
        decrypted_token = secret_service.decrypt_token(connection.access_token)
        return ConnectorFactory.create(
            provider, credentials, access_token=decrypted_token
        )


integration_service = IntegrationService()
