import asyncio
import json
import logging
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


LOGGER = logging.getLogger("model_service")


def configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")


def build_error_response(status_code: int, request_id: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "request_id": request_id,
                "detail": detail,
            }
        },
    )


def get_request_id(request: Request) -> str:
    header_name = request.app.state.request_id_header
    incoming_request_id = request.headers.get(header_name)
    return incoming_request_id.strip() if incoming_request_id else uuid4().hex


def log_request_event(
    *,
    request: Request,
    status_code: int,
    success: bool,
    duration_ms: float,
    detail: str | None = None,
) -> None:
    backend_name = getattr(request.state, "backend_name", "unknown")
    model_id = getattr(request.state, "model_id", None)
    request_id = getattr(request.state, "request_id", "unknown")
    event = {
        "timestamp": getattr(request.state, "started_at_iso", None),
        "request_id": request_id,
        "method": request.method,
        "endpoint": request.url.path,
        "backend": backend_name,
        "model_id": model_id,
        "duration_ms": round(duration_ms, 2),
        "success": success,
        "status_code": status_code,
    }
    if detail:
        event["detail"] = detail
    LOGGER.info(json.dumps(event, sort_keys=True))


async def enter_request_slot(request: Request) -> str | None:
    async with request.app.state.inflight_lock:
        if request.app.state.inflight_requests >= request.app.state.max_concurrent_requests:
            return (
                f"model-service is at capacity: "
                f"{request.app.state.inflight_requests}/"
                f"{request.app.state.max_concurrent_requests} in-flight requests"
            )
        request.app.state.inflight_requests += 1
    return None


async def leave_request_slot(request: Request) -> None:
    async with request.app.state.inflight_lock:
        request.app.state.inflight_requests = max(0, request.app.state.inflight_requests - 1)


async def run_with_timeout(request: Request, call_next):
    return await asyncio.wait_for(call_next(request), timeout=request.app.state.request_timeout_seconds)
