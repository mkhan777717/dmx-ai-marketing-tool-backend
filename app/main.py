from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.logger import logger
from app.exceptions.handlers import register_exception_handlers
from app.middleware.cors import add_cors_middleware
from app.middleware.logging import log_requests
from app.middleware.timing import add_process_time_header
from app.operations.admin.router import router as admin_router
from app.operations.announcements.router import router as announcements_router
from app.operations.audit.router import router as audit_router
from app.operations.configuration.router import router as config_router
from app.operations.feature_flags.router import router as feature_flags_router
from app.operations.logging.middleware import CorrelationIdMiddleware
from app.operations.maintenance.middleware import MaintenanceModeMiddleware
from app.operations.monitoring.health import router as ops_health_router
from app.api.v1.endpoints.health import router as health_router


logger.info("Starting AI Marketing Suite Backend")

app = FastAPI(
    title="AI Marketing Suite API",
    version="1.0.0",
    description="Backend API for AI Marketing Suite",
)


# Register Middleware
async def get_maintenance_mode():
    return "NORMAL"  # In production, this would query Redis/ConfigService


app.add_middleware(
    MaintenanceModeMiddleware, get_maintenance_state_callback=get_maintenance_mode
)
app.add_middleware(CorrelationIdMiddleware)
app.middleware("http")(log_requests)
app.middleware("http")(add_process_time_header)

add_cors_middleware(app)

# exception handlers
register_exception_handlers(app)

# Register Operations Health router
app.include_router(ops_health_router)

# Register API Routes
app.include_router(
    api_router,
    prefix="/api/v1",
)

app.include_router(audit_router)
app.include_router(admin_router)
app.include_router(feature_flags_router)
app.include_router(config_router)
app.include_router(announcements_router)

app.include_router(health_router)
