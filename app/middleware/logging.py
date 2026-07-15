from fastapi import Request

from app.core.logger import logger


async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")

    response = await call_next(request)

    logger.info(
        f"Response: {response.status_code} {request.method} {request.url.path}"
    )

    return response