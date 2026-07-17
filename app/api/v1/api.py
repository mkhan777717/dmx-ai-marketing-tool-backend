from fastapi import APIRouter

api_router = APIRouter()

# Example:
# from app.api.v1.endpoints import auth
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
from app.api.v1.campaign_schedule import router as campaign_schedule_router
api_router.include_router(campaign_schedule_router)
