import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings


@pytest.fixture
async def async_db():
    async_url = (
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        if settings.DATABASE_URL.startswith("postgresql://")
        else settings.DATABASE_URL
    )
    engine = create_async_engine(
        async_url, pool_pre_ping=True, connect_args={"statement_cache_size": 0}
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


from app.db.session import get_db_session


@pytest.fixture(autouse=True)
def override_dependencies(async_db):
    app.dependency_overrides[get_db_session] = lambda: async_db
    yield
    app.dependency_overrides.clear()
