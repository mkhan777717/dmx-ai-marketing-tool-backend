from pydantic import computed_field
from pydantic_settings import BaseSettings


class RedisSettings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @computed_field
    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
