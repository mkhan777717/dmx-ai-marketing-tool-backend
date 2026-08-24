import base64
import hashlib
import logging
import secrets
import urllib.parse
from typing import Any

from app.integrations.constants import META_GRAPH_API_VERSION

logger = logging.getLogger(__name__)


class OAuthManager:
    """
    Manages OAuth flows, CSRF states, and redirect URIs for various providers.
    """

    # In a real app, state should be stored in Redis with expiration to prevent CSRF.
    # For now, we will assume a simple dictionary or rely on client-side state.
    _states: dict[str, dict[str, Any]] = {}

    # Providers that require PKCE
    _PKCE_PROVIDERS = {"x", "twitter"}

    @staticmethod
    def _generate_pkce_verifier() -> str:
        # Generates a 43-character URL-safe random string
        return secrets.token_urlsafe(32)

    @staticmethod
    def _generate_pkce_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    @staticmethod
    def generate_state(workspace_id: str, provider: str) -> str:
        state = secrets.token_urlsafe(32)
        provider_lower = provider.lower()

        state_data: dict[str, Any] = {
            "workspace_id": str(workspace_id),
            "provider": provider,
            "code_verifier": None,
        }

        if provider_lower in OAuthManager._PKCE_PROVIDERS:
            state_data["code_verifier"] = OAuthManager._generate_pkce_verifier()

        OAuthManager._states[state] = state_data
        return state

    @staticmethod
    def validate_state(state: str) -> dict[str, Any] | None:
        return OAuthManager._states.pop(state, None)

    @staticmethod
    def get_authorization_url(
        provider: str, state: str, redirect_uri: str, client_id: str
    ) -> str:
        provider = provider.lower()

        state_data = OAuthManager._states.get(state)
        code_challenge = None
        if state_data and state_data.get("code_verifier"):
            code_challenge = OAuthManager._generate_pkce_challenge(
                state_data["code_verifier"]
            )

        if provider == "slack":
            return f"https://slack.com/oauth/v2/authorize?client_id={client_id}&state={state}&redirect_uri={redirect_uri}&scope=chat:write,commands"
        if provider == "mock":
            return f"https://mockprovider.com/oauth/authorize?client_id={client_id}&state={state}&redirect_uri={redirect_uri}"
        if provider == "google":
            scopes = " ".join(
                [
                    "openid",
                    "email",
                    "profile",
                    "https://www.googleapis.com/auth/business.manage",
                    "https://www.googleapis.com/auth/youtube.upload",
                ]
            )
            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "scope": scopes,
                "access_type": "offline",
                "prompt": "consent",
            }
            query = urllib.parse.urlencode(params)
            return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

        if provider == "facebook":
            scopes = "pages_show_list,pages_read_engagement,pages_manage_posts"

            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "scope": scopes,
            }
            query = urllib.parse.urlencode(params)
            return f"https://www.facebook.com/{META_GRAPH_API_VERSION}/dialog/oauth?{query}"

        if provider == "instagram":
            scopes = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "scope": scopes,
            }
            query = urllib.parse.urlencode(params)
            return f"https://www.facebook.com/{META_GRAPH_API_VERSION}/dialog/oauth?{query}"

        if provider in OAuthManager._PKCE_PROVIDERS:
            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
            # Add some default scopes for testing the URL generation structure
            if provider in {"x", "twitter"}:
                params["scope"] = "tweet.read tweet.write users.read offline.access"

            query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
            return f"https://twitter.com/i/oauth2/authorize?{query}"

        raise ValueError(f"Unsupported provider for OAuth: {provider}")
