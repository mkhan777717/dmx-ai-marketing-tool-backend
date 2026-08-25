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
    state = OAuthManager.generate_state(str(workspace.id), provider)
    credentials = secret_service.get_provider_credentials(provider)

    if not credentials["client_id"]:
        raise HTTPException(
            status_code=500, detail=f"Client ID not configured for provider {provider}"
        )

    url = OAuthManager.get_authorization_url(
        provider, state, redirect_uri, credentials["client_id"]
    )
    return ApiResponse(
        success=True, message="OAuth URL generated", data={"url": url, "state": state}
    )


@router.get("/oauth/callback", response_model=ApiResponse)
async def oauth_callback(
    state: str, code: str, db: AsyncSession = Depends(get_db_session)
) -> Any:
    """Handle OAuth callback, exchange code for tokens, and store them."""
    state_data = OAuthManager.validate_state(state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    workspace_id = uuid.UUID(state_data["workspace_id"])
    provider = state_data["provider"]
    code_verifier = state_data.get("code_verifier")

    # We exchange the code inside connect_provider using the connector
    await integration_service.connect_provider(
        db, workspace_id, provider, code, code_verifier=code_verifier
    )
    await db.commit()

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


@router.post("/webhooks/{provider}")
async def receive_webhook(
    provider: str, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    """Generic endpoint to receive webhooks from providers."""
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

    # We assume the provider payload contains some info mapping it to a workspace.
    # In a real app, this requires provider-specific parsing.
    # For this abstraction, we will use a dummy workspace ID or parse it.
    workspace_id = payload.get("workspace_id") or payload.get("mock_account_id")
    if not workspace_id:
        # Cannot route this webhook
        raise HTTPException(
            status_code=400, detail="Could not determine workspace from payload"
        )

    if isinstance(workspace_id, str):
        try:
            workspace_id = uuid.UUID(workspace_id)
        except ValueError:
            pass  # We leave it as string, but dispatcher expects UUID. Will handle later.

    # Dispatch Event (this is fire and forget, usually)
    await WebhookDispatcher.dispatch(db, provider, payload, workspace_id)

    return {"status": "accepted"}
