import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.operations.logging.context import (
    correlation_id_ctx,
    request_id_ctx,
    reset_context_var,
    set_context_var,
)
from app.operations.logging.logger import structured_logger


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Injects request_id and correlation_id into the context for structured logging.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract correlation ID from headers or generate a new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request_id = str(uuid.uuid4())

        # Set context variables
        req_token = set_context_var(request_id_ctx, request_id)
        corr_token = set_context_var(correlation_id_ctx, correlation_id)

        start_time = time.time()

        # Log incoming request
        structured_logger.info(f"Incoming request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id

            structured_logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "status_code": response.status_code,
                    "duration": round(duration, 4),
                },
            )
            return response
        except Exception:
            duration = time.time() - start_time
            structured_logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra={"status_code": 500, "duration": round(duration, 4)},
            )
            raise
        finally:
            # Clean up context variables
            reset_context_var(request_id_ctx, req_token)
            reset_context_var(correlation_id_ctx, corr_token)
