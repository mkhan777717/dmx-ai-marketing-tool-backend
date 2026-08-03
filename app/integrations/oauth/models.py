import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class ConnectionStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"


class IntegrationConnection(Base, TimestampMixin):
    __tablename__ = "integration_connections"

    workspace_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    status: Mapped[ConnectionStatus] = mapped_column(
        SQLEnum(ConnectionStatus), default=ConnectionStatus.PENDING, nullable=False
    )

    # Encrypted credentials
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    metadata_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
