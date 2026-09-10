from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings


def add_cors_middleware(app):
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if hasattr(settings, "FRONTEND_URL") and settings.FRONTEND_URL:
        for url in settings.FRONTEND_URL.split(","):
            cleaned_url = url.strip().rstrip("/")
            if cleaned_url and cleaned_url not in origins:
                origins.append(cleaned_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
