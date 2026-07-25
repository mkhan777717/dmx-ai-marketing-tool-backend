from typing import Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T")

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T | dict = {}
    meta: dict[str, Any] = {}

# Alias used by endpoints
ApiResponse = SuccessResponse

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: list[dict[str, Any]] | None = None
