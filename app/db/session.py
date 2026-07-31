from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings

engine = None
SessionLocal = None
async_engine = None
AsyncSessionLocal = None

if settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    async_url = (
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        if settings.DATABASE_URL.startswith("postgresql://")
        else settings.DATABASE_URL
    )
    async_engine = create_async_engine(
        async_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
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
    Dependency that provides a SQLAlchemy database session.
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
    Dependency that provides an asynchronous SQLAlchemy database session.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Async Database is not configured.")

    async with AsyncSessionLocal() as session:
        yield session
