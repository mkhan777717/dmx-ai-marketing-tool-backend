import base64
import os

from cryptography.fernet import Fernet

from app.integrations.secrets.adapters.environment import (
    EnvironmentSecretAdapter,
    SecretAdapter,
)


class SecretService:
    def __init__(self, adapter: SecretAdapter = EnvironmentSecretAdapter()):
        self.adapter = adapter
        # Provide a default fallback key for local dev if not set
        key = self.adapter.get_secret("ENCRYPTION_KEY")
        if not key:
            # Fallback 32 url-safe base64-encoded bytes for local dev
            key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        self.fernet = Fernet(key)

    def get_provider_credentials(self, provider: str) -> dict[str, str]:
        """Fetch client_id, client_secret, and signing_secret for a given provider from the secret adapter."""
        provider_upper = provider.upper()
        client_id = self.adapter.get_secret(f"{provider_upper}_CLIENT_ID") or ""
        client_secret = self.adapter.get_secret(f"{provider_upper}_CLIENT_SECRET") or ""
        signing_secret = (
            self.adapter.get_secret(f"{provider_upper}_SIGNING_SECRET") or ""
        )

        # Instagram & WhatsApp reuse Meta/Facebook App credentials if specific provider credentials are not set
        if provider_upper in ("INSTAGRAM", "WHATSAPP") and not client_id:
            client_id = (
                self.adapter.get_secret("FACEBOOK_CLIENT_ID")
                or self.adapter.get_secret("META_CLIENT_ID")
                or ""
            )
            client_secret = (
                self.adapter.get_secret("FACEBOOK_CLIENT_SECRET")
                or self.adapter.get_secret("META_CLIENT_SECRET")
                or ""
            )

        # YouTube reuses Google credentials if specific provider credentials are not set
        if provider_upper == "YOUTUBE" and not client_id:
            client_id = self.adapter.get_secret("GOOGLE_CLIENT_ID") or ""
            client_secret = self.adapter.get_secret("GOOGLE_CLIENT_SECRET") or ""

        developer_token = (
            self.adapter.get_secret("GOOGLE_ADS_DEVELOPER_TOKEN")
            or self.adapter.get_secret(f"{provider_upper}_DEVELOPER_TOKEN")
            or ""
        )

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "signing_secret": signing_secret,
            "developer_token": developer_token,
        }

    def get_secret(self, secret_name: str) -> str | None:
        """Fetch a secret directly by name from the secret adapter."""
        return self.adapter.get_secret(secret_name)

    def encrypt_token(self, token: str) -> str:
        if not token:
            return token
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return encrypted_token
        try:
            return self.fernet.decrypt(encrypted_token.encode()).decode()
        except Exception:
            # If we can't decrypt, it might not be encrypted or key changed
            return encrypted_token


secret_service = SecretService()
