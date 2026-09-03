"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="ServiceFlow IL", version="0.1.0")


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    """Report whether the application process can serve requests."""
    return {"status": "ok"}
