from typing import Any, TypeVar

from app.schemas.responses import SuccessResponse

T = TypeVar("T")


def build_success_response(
    message: str, data: T | dict = None, meta: dict[str, Any] = None
) -> dict:
    return SuccessResponse(
        message=message, data=data or {}, meta=meta or {}
    ).model_dump()
