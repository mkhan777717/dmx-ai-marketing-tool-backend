from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.workspaces import router as workspaces_router
from app.api.v1.endpoints.members import router as members_router
from app.api.v1.endpoints.invites import router as invites_router

api_router = APIRouter()

api_router.include_router(
    health_router,
    tags=["Health"],
)

api_router.include_router(
    workspaces_router,
    prefix="/workspaces",
    tags=["Workspaces"],
)

api_router.include_router(
    members_router,
    prefix="/workspaces",
    tags=["Members"],
)

api_router.include_router(
    invites_router,
    tags=["Invites"],
)

from app.api.v1.campaign_schedule import router as campaign_schedule_router
api_router.include_router(campaign_schedule_router)
