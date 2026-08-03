from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import AsyncSessionLocal
from app.services.supabase_auth import SupabaseAuthService


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip auth for health checks or public endpoints if needed
        if request.url.path.startswith(("/health", "/docs", "/openapi.json")):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # For dependencies, we let the dependency handle the error or here we can return 401
            # But since we use Depends(security), it's often better to let dependencies handle strict enforcement.
            # We just parse the token if it exists.
            request.state.user = None
            return await call_next(request)

        token = auth_header.split(" ")[1]
        try:
            payload = SupabaseAuthService.verify_jwt(token)
            async with AsyncSessionLocal() as db:
                user = await SupabaseAuthService.get_or_create_user(db, payload)
                request.state.user = user

        except Exception:
            # Let it fail silently here or return 401. If we enforce strictly at middleware:
            # return JSONResponse(status_code=401, content={"detail": str(e)})
            request.state.user = None

        return await call_next(request)
