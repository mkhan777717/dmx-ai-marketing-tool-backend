from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {
        "message": "AI Marketing Suite Backend is running"
    }


@router.get("/health")
async def health():
    return {
        "status": "healthy"
    }
