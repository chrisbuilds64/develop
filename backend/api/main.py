"""
FastAPI Entry Point
"""
from fastapi import FastAPI

from infrastructure.logging import get_logger
from api.routes import items

logger = get_logger("api")

app = FastAPI(
    title="ChrisBuilds64 API",
    version="0.1.0"
)

# Register routes
app.include_router(items.router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}
