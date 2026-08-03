import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """
    Blocks or limits access based on system maintenance modes.
    Expects runtime config to dictate state.
    """

    def __init__(self, app, get_maintenance_state_callback=None):
        super().__init__(app)
        self.get_maintenance_state = get_maintenance_state_callback

    async def dispatch(self, request: Request, call_next):
        if not self.get_maintenance_state:
            return await call_next(request)

        # Bypass admin paths or health checks
        if request.url.path.startswith("/api/v1/health") or request.url.path.startswith(
            "/api/v1/admin"
        ):
            return await call_next(request)

        # In a real async middleware without blocking, we'd use a fast cache lookup (Redis).
        # We assume the callback is fast/cached.
        mode = await self.get_maintenance_state()

        if mode == "MAINTENANCE":
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "System is currently undergoing maintenance. Please try again later."
                },
            )
        elif mode == "READ_ONLY" and request.method not in ("GET", "HEAD", "OPTIONS"):
            return JSONResponse(
                status_code=403,
                content={"detail": "System is in read-only mode for maintenance."},
            )

        return await call_next(request)
