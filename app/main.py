from fastapi import FastAPI

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