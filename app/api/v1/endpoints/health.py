from fastapi import APIRouter

from app.config.settings import settings

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "AI Marketing Suite Backend is running"}


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
    }
