from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Marketing Suite"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "AI Marketing Platform"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Frontend URL
    FRONTEND_URL: str = "https://dmx-ai-marketing-tool-frontend-delta.vercel.app"

    # Database
    DATABASE_URL: str | None = None
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    @computed_field
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace(
                    "postgresql://", "postgresql+asyncpg://"
                )
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Supabase
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_JWT_SECRET: str = "super-secret-jwt-token-with-at-least-32-characters-long"
    SUPABASE_STORAGE_BUCKET: str = "campaign-assets"

    # Encryption & Security
    ENCRYPTION_KEY: str = "your-32-byte-base64-encoded-secret-key-here"
    SECRET_KEY: str = "default-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Facebook
    FACEBOOK_CLIENT_ID: str | None = None
    FACEBOOK_CLIENT_SECRET: str | None = None
    FACEBOOK_REDIRECT_URI: str | None = None
    FACEBOOK_CONFIG_ID: str | None = None

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    @computed_field
    @property
    def REDIS_URI(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
