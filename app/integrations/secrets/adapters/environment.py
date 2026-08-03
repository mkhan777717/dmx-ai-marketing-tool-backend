import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)


class SecretAdapter(Protocol):
    def get_secret(self, key: str) -> str | None: ...


class EnvironmentSecretAdapter(SecretAdapter):
    def get_secret(self, key: str) -> str | None:
        return os.environ.get(key)


class VaultSecretAdapter(SecretAdapter):
    def get_secret(self, key: str) -> str | None:
        # Placeholder for HashiCorp Vault implementation
        return None


class AWSSecretAdapter(SecretAdapter):
    def get_secret(self, key: str) -> str | None:
        # Placeholder for AWS Secrets Manager implementation
        return None
