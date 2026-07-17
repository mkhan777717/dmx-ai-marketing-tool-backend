from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/")
async def root():
    return {
        "message": "AI Marketing Suite Backend is running"
    }


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health():
    return HealthResponse(
        status="healthy"
    )