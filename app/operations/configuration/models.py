import enum
import uuid

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class DataType(enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    JSON = "json"


class RuntimeConfiguration(Base, TimestampMixin):
    """
    Global runtime configuration settings that can be updated dynamically
    without restarting the application.
    """

    __tablename__ = "runtime_configurations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    data_type: Mapped[DataType] = mapped_column(
        Enum(DataType), default=DataType.STRING, nullable=False
    )
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
