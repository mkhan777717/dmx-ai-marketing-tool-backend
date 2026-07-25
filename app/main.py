from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.logger import logger

from app.middleware.cors import add_cors_middleware
from app.middleware.logging import log_requests
from app.middleware.timing import add_process_time_header

from app.exceptions.handlers import register_exception_handlers

logger.info("Starting AI Marketing Suite Backend")

app = FastAPI(
    title="AI Marketing Suite API",
    version="1.0.0",
    description="Backend API for AI Marketing Suite",
)

# Register Middleware
app.middleware("http")(log_requests)
app.middleware("http")(add_process_time_header)

add_cors_middleware(app)

#exception handlers
register_exception_handlers(app)

# Register health at root level (no prefix) for /health
from app.api.v1.endpoints.health import router as health_router
app.include_router(health_router)

# Register API Routes
app.include_router(
    api_router,
    prefix="/api/v1",
)