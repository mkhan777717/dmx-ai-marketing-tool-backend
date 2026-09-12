from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config.settings import settings

engine = None
SessionLocal = None
async_engine = None
AsyncSessionLocal = None

db_url = settings.DATABASE_URL or getattr(settings, "ASYNC_DATABASE_URI", None)

if db_url:
    sync_url = (
        db_url.replace("postgresql+asyncpg://", "postgresql://")
        if db_url.startswith("postgresql+asyncpg://")
        else db_url
    )

    sync_connect_args = (
        {"sslmode": "require"}
        if "localhost" not in sync_url and "127.0.0.1" not in sync_url
        else {}
    )

    engine = create_engine(
        sync_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        connect_args=sync_connect_args,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    async_url = (
        db_url.replace("postgresql://", "postgresql+asyncpg://")
        if db_url.startswith("postgresql://")
        else db_url
    )

    async_engine = create_async_engine(
        async_url,
        echo=settings.DEBUG,
        future=True,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
        },
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )


def get_db():
    """
    Sync DB dependency.
    """
    if SessionLocal is None:
        raise RuntimeError("Database is not configured.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db_session():
    """
    Async DB dependency.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Async Database is not configured.")

    async with AsyncSessionLocal() as session:
        yield session
