import logging
import uuid
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
        db: AsyncSession, workspace_id: uuid.UUID, provider: str, auth_code: str
    ) -> IntegrationConnection:
        provider = provider.lower()
        credentials = secret_service.get_provider_credentials(provider)

        # Instantiate Connector
        connector = ConnectorFactory.create(provider, credentials)

        # Retrieve circuit breaker
        breaker = get_circuit_breaker(provider)

        try:
            # Connect and exchange tokens via circuit breaker and retry policy
            @retry_policy(max_retries=2)
            async def _connect():
                return await breaker.call(connector.connect, auth_code)

            metadata = await _connect()
            access_token = metadata.pop("access_token", None)
            refresh_token = metadata.pop("refresh_token", None)
            expires_at = metadata.pop("expires_at", None)

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
                updated = await integration_connection_repo.update(
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
                return updated
            else:
                new_conn = await integration_connection_repo.create(
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
                return new_conn

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
