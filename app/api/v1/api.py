from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router

api_router = APIRouter()

api_router.include_router(
    health_router,
    tags=["Health"],
)

# TODO: Enable after authentication dependencies
# (get_current_user/get_current_workspace) are implemented.
# from app.api.v1.campaign_schedule import router as campaign_schedule_router
# api_router.include_router(campaign_schedule_router)