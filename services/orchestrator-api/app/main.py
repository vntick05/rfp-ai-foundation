from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import check_database

app = FastAPI(title="orchestrator-api", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> JSONResponse:
    settings = get_settings()
    db_ok = False
    detail = "database connection not verified"
    try:
        db_ok = await check_database()
        detail = "database connection ok" if db_ok else "database connection failed"
    except Exception as exc:
        detail = f"database connection failed: {exc.__class__.__name__}"

    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if db_ok else "degraded",
            "service": "orchestrator-api",
            "environment": settings.app_env,
            "database": {
                "configured": bool(settings.database_url),
                "reachable": db_ok,
                "detail": detail,
            },
        },
    )
