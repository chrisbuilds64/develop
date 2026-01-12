"""
FastAPI Entry Point
"""
from fastapi import FastAPI

from infrastructure.logging import get_logger

logger = get_logger("api")

app = FastAPI(
    title="ChrisBuilds64 API",
    version="0.1.0"
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}
