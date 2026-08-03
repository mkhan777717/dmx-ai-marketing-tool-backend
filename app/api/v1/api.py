from fastapi import APIRouter

from app.api.v1.campaign_schedule import router as campaign_schedule_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.campaign_content import router as campaign_content_router
from app.api.v1.endpoints.campaigns import router as campaigns_router
from app.api.v1.endpoints.integrations import router as integrations_router
from app.api.v1.endpoints.invites import router as invites_router
from app.api.v1.endpoints.members import router as members_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.publishing import router as publishing_router
from app.api.v1.endpoints.social_accounts import router as social_accounts_router
from app.api.v1.endpoints.workspaces import router as workspaces_router

api_router = APIRouter()

api_router.include_router(
    workspaces_router,
    prefix="/workspaces",
    tags=["Workspaces"],
)

api_router.include_router(
    integrations_router,
    prefix="/integrations",
    tags=["Integrations"],
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

api_router.include_router(
    campaigns_router,
    prefix="/workspaces",
    tags=["Campaigns"],
)

api_router.include_router(
    campaign_content_router,
    prefix="/workspaces",
    tags=["Campaign Content & AI"],
)

api_router.include_router(
    social_accounts_router,
    prefix="/workspaces",
    tags=["Social Accounts"],
)

api_router.include_router(
    publishing_router,
    prefix="/workspaces",
    tags=["Social Publishing"],
)

api_router.include_router(
    analytics_router,
    prefix="/workspaces",
    tags=["Analytics"],
)

api_router.include_router(
    notifications_router,
    prefix="/notifications",
    tags=["Notifications"],
)

api_router.include_router(
    campaign_schedule_router,
)
