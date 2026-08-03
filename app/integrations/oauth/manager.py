import logging
import secrets
from typing import Any

logger = logging.getLogger(__name__)


class OAuthManager:
    """
    Manages OAuth flows, CSRF states, and redirect URIs for various providers.
    """

    # In a real app, state should be stored in Redis with expiration to prevent CSRF.
    # For now, we will assume a simple dictionary or rely on client-side state.
    _states: dict[str, dict[str, Any]] = {}

    @staticmethod
    def generate_state(workspace_id: str, provider: str) -> str:
        state = secrets.token_urlsafe(32)
        OAuthManager._states[state] = {
            "workspace_id": str(workspace_id),
            "provider": provider,
        }
        return state

    @staticmethod
    def validate_state(state: str) -> dict[str, Any] | None:
        return OAuthManager._states.pop(state, None)

    @staticmethod
    def get_authorization_url(
        provider: str, state: str, redirect_uri: str, client_id: str
    ) -> str:
        provider = provider.lower()
        if provider == "slack":
            return f"https://slack.com/oauth/v2/authorize?client_id={client_id}&state={state}&redirect_uri={redirect_uri}&scope=chat:write,commands"
        if provider == "mock":
            return f"https://mockprovider.com/oauth/authorize?client_id={client_id}&state={state}&redirect_uri={redirect_uri}"

        raise ValueError(f"Unsupported provider for OAuth: {provider}")
