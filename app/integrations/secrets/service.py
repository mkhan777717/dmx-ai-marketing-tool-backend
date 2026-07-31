import base64
import os

from cryptography.fernet import Fernet

from app.integrations.secrets.adapters.environment import (
    EnvironmentSecretAdapter, SecretAdapter)


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
        """Fetch client_id and client_secret for a given provider from the secret adapter."""
        client_id = self.adapter.get_secret(f"{provider.upper()}_CLIENT_ID") or ""
        client_secret = (
            self.adapter.get_secret(f"{provider.upper()}_CLIENT_SECRET") or ""
        )
        return {"client_id": client_id, "client_secret": client_secret}

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
