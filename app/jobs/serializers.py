import json
import uuid
from typing import Any

from pydantic import BaseModel


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        return super().default(obj)


class JobSerializer:
    @staticmethod
    def serialize(payload: dict | BaseModel) -> dict:
        """
        Serializes payload safely for Redis transport.
        """
        if isinstance(payload, BaseModel):
            return json.loads(json.dumps(payload.model_dump(), cls=UUIDEncoder))
        return json.loads(json.dumps(payload, cls=UUIDEncoder))
