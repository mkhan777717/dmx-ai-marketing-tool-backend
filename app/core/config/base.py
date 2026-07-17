from pydantic_settings import BaseSettings

class AppBaseSettings(BaseSettings):
    PROJECT_NAME: str = "AI Marketing Platform"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
