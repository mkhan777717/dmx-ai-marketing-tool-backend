import uuid

import pytest
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

from app.repositories.base import BaseRepository

Base = declarative_base(metadata=MetaData())


class RepoDummyModel(Base):
    __tablename__ = "repo_dummy"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column()


class DummyRepository(BaseRepository[RepoDummyModel]):
    pass


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_create_and_get(async_db: AsyncSession):
    repo = DummyRepository(RepoDummyModel)

    # Test Create
    obj = await repo.create(async_db, obj_in={"name": "test_name"})
    assert obj.id is not None
    assert obj.name == "test_name"

    # Test Get
    fetched_obj = await repo.get_by_id(async_db, obj.id)
    assert fetched_obj is not None
    assert fetched_obj.id == obj.id

    # Test Count
    count = await repo.count(async_db)
    assert count == 1

    # Test Exists
    exists = await repo.exists(async_db, obj.id)
    assert exists is True
