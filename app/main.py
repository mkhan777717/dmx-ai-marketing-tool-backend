from fastapi import FastAPI

from app.core.logger import logger
logger.info("Starting AI Marketing Suite Backend")

app = FastAPI(
    title="AI Marketing Suite API",
    version="1.0.0",
    description="Backend API for AI Marketing Suite",
)

@app.get("/")
async def root():
    return {
        "message": "AI Marketing Suite Backend is running"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }