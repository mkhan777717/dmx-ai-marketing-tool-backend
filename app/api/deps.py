import uuid
from app.db.models.user import User

async def get_current_user() -> User:
    """Mock user dependency to allow the app to boot."""
    return User(id=uuid.uuid4(), email="test@example.com")

async def get_current_workspace() -> uuid.UUID:
    """Mock workspace dependency to allow the app to boot."""
    return uuid.uuid4()
