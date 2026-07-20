from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings

engine = None
SessionLocal = None

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