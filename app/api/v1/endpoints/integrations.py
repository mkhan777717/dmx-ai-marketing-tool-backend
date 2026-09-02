import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_workspace, require_permission
from app.db.session import get_db_session
from app.integrations.oauth.manager import OAuthManager
from app.integrations.oauth.service import integration_service
from app.integrations.secrets.service import secret_service
from app.integrations.sync.engine import sync_engine
from app.integrations.webhooks.dispatcher import WebhookDispatcher
from app.integrations.webhooks.verifier import WebhookVerifier
from app.models.workspace import Workspace
from app.schemas.responses import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ApiResponse)
async def list_integrations(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("integration", "read")),
) -> Any:
    """List active integration connections for the workspace."""
    connections = await integration_service.list_connections(db, workspace.id)
    # Serialize safely
    data = [
        {
            "id": str(c.id),
            "provider": c.provider,
            "status": c.status.value,
            "expires_at": c.expires_at,
        }
        for c in connections
    ]
    return ApiResponse(success=True, message="Integrations retrieved", data=data)


@router.get("/oauth/{provider}/url", response_model=ApiResponse)
async def get_oauth_url(
    provider: str,
    redirect_uri: str,
    workspace: Workspace = Depends(get_current_workspace),
    _: bool = Depends(require_permission("integration", "manage")),
) -> Any:
    """Get the authorization URL for a specific provider."""
    state = OAuthManager.generate_state(
        str(workspace.id), provider, redirect_uri=redirect_uri
    )
    credentials = secret_service.get_provider_credentials(provider)

    if not credentials["client_id"]:
        raise HTTPException(
            status_code=500, detail=f"Client ID not configured for provider {provider}"
        )

    from app.config.settings import settings

    config_id = (
        settings.FACEBOOK_CONFIG_ID
        if provider.lower() in ("facebook", "instagram", "whatsapp")
        else None
    )

    url = OAuthManager.get_authorization_url(
        provider, state, redirect_uri, credentials["client_id"], config_id=config_id
    )
    return ApiResponse(
        success=True, message="OAuth URL generated", data={"url": url, "state": state}
    )


@router.get("/oauth/callback", response_model=ApiResponse)
async def oauth_callback(
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    error_uri: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    """Handle OAuth callback, exchange code for tokens, and store them safely."""
    import hashlib

    code_fp = hashlib.sha256(code.encode()).hexdigest()[:10] if code else "none"
    state_fp = state[:8] if state else "none"

    if error:
        detail_msg = error_description or error
        if state:
            OAuthManager.validate_state(state)
        logger.warning(
            f"[OAuth Callback] Failure response received: state_prefix={state_fp}, error={error}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authorization failed: {detail_msg}",
        )

    if not code or not state:
        logger.warning("[OAuth Callback] Missing code or state in callback request.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code or state parameter from OAuth callback",
        )

    state_data = OAuthManager.validate_state(state)
    if not state_data:
        logger.warning(
            f"[OAuth Callback] Invalid or expired state: state_prefix={state_fp}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )

    workspace_id = uuid.UUID(state_data["workspace_id"])
    provider = state_data["provider"]
    code_verifier = state_data.get("code_verifier")
    redirect_uri = state_data.get("redirect_uri")

    logger.info(
        f"[OAuth Callback] Processing: provider={provider}, workspace_id={workspace_id}, code_fp={code_fp}, redirect_uri={redirect_uri}"
    )

    try:
        await integration_service.connect_provider(
            db,
            workspace_id,
            provider,
            code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        err_msg = str(exc)
        if (
            "client_secret" in err_msg
            or "access_token" in err_msg
            or "Bearer" in err_msg
        ):
            err_msg = "Token exchange failed with provider."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect integration: {err_msg}",
        ) from exc

    try:
        from app.integrations.sync.engine import sync_engine

        await sync_engine.execute_sync_job(
            db,
            {
                "workspace_id": str(workspace_id),
                "provider": provider,
                "sync_type": "full",
            },
        )
        await db.commit()
    except Exception as sync_exc:
        logger.warning(
            f"Initial sync for provider {provider} workspace {workspace_id} raised: {sync_exc}"
        )

    return ApiResponse(success=True, message=f"Successfully connected to {provider}")


@router.post("/{provider}/sync", response_model=ApiResponse)
async def trigger_sync(
    provider: str,
    sync_type: str = "full",
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("integration", "manage")),
) -> Any:
    """Trigger a manual sync for an integration."""
    result = await sync_engine.trigger_sync(db, workspace.id, provider, sync_type)
    return ApiResponse(success=True, message="Sync job enqueued", data=result)


@router.delete("/{provider}", response_model=ApiResponse)
async def disconnect_integration(
    provider: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("integration", "manage")),
) -> Any:
    """Disconnect and revoke an integration."""
    await integration_service.disconnect_provider(db, workspace.id, provider)
    await db.commit()
    return ApiResponse(
        success=True, message=f"Successfully disconnected from {provider}"
    )


@router.get("/webhooks/{provider}")
async def verify_webhook_subscription(
    provider: str,
    request: Request,
) -> Any:
    """GET endpoint to verify Meta/WhatsApp webhook subscriptions."""
    import os

    from fastapi.responses import PlainTextResponse

    from app.integrations.exceptions import WebhookVerificationError

    provider_name = provider.lower()
    params = dict(request.query_params)
    mode = params.get("hub.mode", "")
    verify_token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    if not mode or not verify_token or not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required webhook verification parameters",
        )

    if provider_name == "whatsapp":
        from app.integrations.connectors.whatsapp.webhook import WhatsAppWebhookHandler

        expected_token = (
            os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
            or os.getenv("META_WEBHOOK_VERIFY_TOKEN")
            or os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "")
        )
        credentials = secret_service.get_provider_credentials("whatsapp")
        handler = WhatsAppWebhookHandler(
            client_secret=credentials.get("client_secret", "")
        )

        try:
            res_challenge = handler.verify_challenge(
                mode=mode,
                verify_token=verify_token,
                challenge=challenge,
                expected_verify_token=expected_token,
            )
            return PlainTextResponse(content=res_challenge)
        except WebhookVerificationError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webhook verification token or mode invalid",
            )

    if provider_name in ("facebook", "instagram", "meta"):
        from app.integrations.connectors.facebook.webhook import FacebookWebhookHandler

        expected_token = os.getenv("META_WEBHOOK_VERIFY_TOKEN") or os.getenv(
            "FACEBOOK_WEBHOOK_VERIFY_TOKEN", ""
        )
        credentials = secret_service.get_provider_credentials("facebook")
        handler = FacebookWebhookHandler(
            client_secret=credentials.get("client_secret", "")
        )

        try:
            res_challenge = handler.verify_challenge(
                mode=mode,
                verify_token=verify_token,
                challenge=challenge,
                expected_verify_token=expected_token,
            )
            return PlainTextResponse(content=res_challenge)
        except WebhookVerificationError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webhook verification token or mode invalid",
            )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Webhook verification not supported for provider '{provider}'",
    )


@router.post("/webhooks/{provider}")
async def receive_webhook(
    provider: str, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    """Generic endpoint to receive webhooks from providers."""
    provider_name = provider.lower()
    body_bytes = await request.body()

    # Verify Signature
    is_valid = await WebhookVerifier.verify_signature(provider, request, body_bytes)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    try:
        payload = await request.json()
    except Exception:
        payload = {"raw_data": body_bytes.decode("utf-8", errors="ignore")}

    workspace_id = None

    if provider_name == "whatsapp":
        from datetime import datetime, timezone

        from app.constants.enums import ApiProvider, PublishStatus
        from app.integrations.connectors.whatsapp.webhook import WhatsAppWebhookHandler
        from app.repositories.publish_history import publish_history_repo
        from app.repositories.social_account import social_account_repo

        credentials = secret_service.get_provider_credentials("whatsapp")
        handler = WhatsAppWebhookHandler(
            client_secret=credentials.get("client_secret", "")
        )
        parsed_data = handler.parse_webhook_payload(payload)

        phone_number_id = parsed_data.get("phone_number_id")
        if phone_number_id:
            accounts = await social_account_repo.get_all(
                db,
                filters={
                    "provider": ApiProvider.WHATSAPP,
                    "account_id": phone_number_id,
                },
            )
            if accounts:
                workspace_id = accounts[0].workspace_id

        # Update PublishHistory statuses
        statuses = parsed_data.get("statuses", [])
        for status_item in statuses:
            msg_id = status_item.get("message_id")
            st = status_item.get("status")
            if not msg_id or not st:
                continue

            records = await publish_history_repo.get_all(
                db, filters={"external_post_id": msg_id}
            )
            if records:
                rec = records[0]
                new_status = PublishStatus.PUBLISHED
                if st == "sent":
                    new_status = PublishStatus.SENT
                elif st == "delivered":
                    new_status = PublishStatus.DELIVERED
                elif st == "read":
                    new_status = PublishStatus.READ
                elif st == "failed":
                    new_status = PublishStatus.FAILED

                # Idempotency check: don't regress status from READ to SENT/DELIVERED
                if rec.status == PublishStatus.READ and new_status in (
                    PublishStatus.SENT,
                    PublishStatus.DELIVERED,
                    PublishStatus.PUBLISHED,
                ):
                    continue

                obj_in: dict[str, Any] = {"status": new_status}
                if new_status == PublishStatus.FAILED:
                    obj_in["error_message"] = (
                        status_item.get("error_detail") or "WhatsApp delivery failed"
                    )
                elif new_status in (
                    PublishStatus.SENT,
                    PublishStatus.DELIVERED,
                    PublishStatus.READ,
                    PublishStatus.PUBLISHED,
                ):
                    if not rec.published_at:
                        obj_in["published_at"] = datetime.now(timezone.utc)

                await publish_history_repo.update(db, db_obj=rec, obj_in=obj_in)
                await db.commit()

        if workspace_id:
            await WebhookDispatcher.dispatch(db, provider, payload, workspace_id)
        return {"status": "accepted"}

    workspace_id = payload.get("workspace_id") or payload.get("mock_account_id")
    if not workspace_id:
        raise HTTPException(
            status_code=400, detail="Could not determine workspace from payload"
        )

    if isinstance(workspace_id, str):
        try:
            workspace_id = uuid.UUID(workspace_id)
        except ValueError:
            pass

    await WebhookDispatcher.dispatch(db, provider, payload, workspace_id)
    return {"status": "accepted"}
