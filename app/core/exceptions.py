from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class BaseAppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


class NotFoundException(BaseAppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)


class UnauthorizedException(BaseAppException):
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message=message, status_code=401)


class ForbiddenException(BaseAppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, status_code=403)


def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )
