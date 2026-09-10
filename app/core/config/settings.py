from pydantic_settings import SettingsConfigDict

from app.core.config.base import AppBaseSettings
from app.core.config.database import DatabaseSettings
from app.core.config.redis import RedisSettings
from app.core.config.security import SecuritySettings


class Settings(AppBaseSettings, DatabaseSettings, RedisSettings, SecuritySettings):
    # Supabase Auth & Storage
    SUPABASE_JWT_SECRET: str = "super-secret-jwt-token-with-at-least-32-characters-long"
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_STORAGE_BUCKET: str = "campaign-assets"

    # Encryption
    ENCRYPTION_KEY: str = "your-32-byte-base64-encoded-secret-key-here"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
