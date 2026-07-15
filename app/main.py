from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging_config import setup_logging
from app.middleware.request_id import RequestIDMiddleware

setup_logging()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="Enterprise SaaS Backend for AI-Powered Digital Marketing Platform",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(RequestIDMiddleware)
    setup_exception_handlers(app)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "environment": settings.ENVIRONMENT}
        
    from app.api.v1.api import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app

app = create_app()
