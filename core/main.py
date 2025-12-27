"""
Tweight Core API - Simple, focused, functional.

Endpoints:
- /health: Service health check
- /timer: Current server timestamp
"""
from datetime import datetime
from fastapi import FastAPI

app = FastAPI(title="Tweight Core API", version="0.1.0")


@app.get("/health")
def health_check():
    """Health check endpoint - always returns OK if service is running."""
    return {"status": "ok", "service": "tweight-core", "version": "0.1.0"}


@app.get("/timer")
def get_timer():
    """Returns current server timestamp."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "unix": int(datetime.utcnow().timestamp())
    }
