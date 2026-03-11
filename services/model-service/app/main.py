import asyncio
from datetime import UTC, datetime
from contextlib import asynccontextmanager
from time import monotonic, time

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.backends.base import ChatMessage, ChatRequest
from app.backends.registry import create_backend
from app.config import get_app_config, get_settings, model_path_exists
from app.observability import (
    build_error_response,
    configure_logging,
    enter_request_slot,
    get_request_id,
    leave_request_slot,
    log_request_event,
    run_with_timeout,
)
from app.schemas import ChatCompletionRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    config = get_app_config()
    configure_logging(settings.log_level)
    app.state.backend = create_backend(config)
    app.state.request_timeout_seconds = config.runtime.request_timeout_seconds
    app.state.max_concurrent_requests = config.runtime.max_concurrent_requests
    app.state.overload_status_code = config.runtime.overload_status_code
    app.state.request_id_header = config.runtime.request_id_header
    app.state.inflight_requests = 0
    app.state.inflight_lock = asyncio.Lock()
    yield


app = FastAPI(title="model-service", version="0.3.0", lifespan=lifespan)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request.state.started_at = monotonic()
    request.state.started_at_iso = datetime.now(UTC).isoformat()
    request.state.request_id = request.headers.get(app.state.request_id_header) or get_request_id(request)
    backend = getattr(app.state, "backend", None)
    request.state.backend_name = backend.descriptor().name if backend else "unknown"
    response = None
    detail = None

    overload_detail = await enter_request_slot(request)
    if overload_detail:
        response = build_error_response(app.state.overload_status_code, request.state.request_id, overload_detail)
        response.headers[app.state.request_id_header] = request.state.request_id
        log_request_event(
            request=request,
            status_code=response.status_code,
            success=False,
            duration_ms=(monotonic() - request.state.started_at) * 1000,
            detail=overload_detail,
        )
        return response

    try:
        response = await run_with_timeout(request, call_next)
    except asyncio.TimeoutError:
        detail = (
            f"request exceeded timeout of {app.state.request_timeout_seconds} seconds"
        )
        response = build_error_response(504, request.state.request_id, detail)
    finally:
        await leave_request_slot(request)

    response.headers[app.state.request_id_header] = request.state.request_id
    log_request_event(
        request=request,
        status_code=response.status_code,
        success=response.status_code < 400,
        duration_ms=(monotonic() - request.state.started_at) * 1000,
        detail=detail,
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    response = build_error_response(exc.status_code, request.state.request_id, detail)
    response.headers[app.state.request_id_header] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    response = build_error_response(422, request.state.request_id, str(exc))
    response.headers[app.state.request_id_header] = request.state.request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    response = build_error_response(500, request.state.request_id, f"Unhandled server error: {exc}")
    response.headers[app.state.request_id_header] = request.state.request_id
    return response


@app.get("/healthz")
def healthz(request: Request) -> dict[str, str]:
    request.state.model_id = get_app_config().model.id
    return {"status": "ok"}


@app.get("/readyz")
def readyz(request: Request) -> JSONResponse:
    settings = get_settings()
    config = get_app_config()
    backend = app.state.backend
    readiness = backend.readiness()
    descriptor = backend.descriptor()
    models = backend.list_models()
    primary_model = models[0] if models else None
    selected_model_path = config.model.path
    selected_runtime_mode = config.model.runtime_mode
    path_exists = model_path_exists(config)
    request.state.model_id = config.model.id

    if primary_model is not None:
        request.state.model_id = primary_model.id
        selected_model_path = (
            primary_model.metadata.get("engine_path")
            or primary_model.metadata.get("model_path")
            or selected_model_path
        )
        selected_runtime_mode = primary_model.runtime_mode
        if selected_model_path:
            from app.config import path_exists as configured_path_exists

            path_exists = configured_path_exists(selected_model_path)

    status_code = 200 if readiness.ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if readiness.ready else "degraded",
            "service": config.service.name,
            "backend": descriptor.__dict__,
            "model": {
                "id": primary_model.id if primary_model else None,
                "path": selected_model_path,
                "path_exists": path_exists,
                "runtime_mode": selected_runtime_mode,
            },
            "environment": settings.app_env,
            "runtime": {
                "request_timeout_seconds": config.runtime.request_timeout_seconds,
                "max_concurrent_requests": config.runtime.max_concurrent_requests,
                "overload_status_code": config.runtime.overload_status_code,
                "request_id_header": config.runtime.request_id_header,
            },
            "detail": readiness.detail,
        },
    )


@app.get("/v1/models")
def list_models(request: Request) -> dict[str, object]:
    backend = app.state.backend
    models = backend.list_models()
    request.state.model_id = models[0].id if models else get_app_config().model.id
    return {
        "object": "list",
        "data": [model.__dict__ for model in models],
    }


@app.post("/v1/chat/completions")
def chat_completions(request: Request, payload: ChatCompletionRequest) -> dict[str, object]:
    backend = app.state.backend
    descriptor = backend.descriptor()
    readiness = backend.readiness()

    if payload.stream:
        raise HTTPException(status_code=501, detail="Streaming is not implemented in this checkpoint")

    if not descriptor.supports_chat:
        raise HTTPException(status_code=501, detail=f"Backend '{descriptor.name}' does not support chat completions")

    if not readiness.ready:
        raise HTTPException(status_code=503, detail=readiness.detail)

    config = get_app_config()
    available_models = {model.id for model in backend.list_models()}
    default_model_id = next(iter(available_models), config.model.id)
    model_id = payload.model or default_model_id
    if model_id not in available_models:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' is not available")
    request.state.model_id = model_id

    response = backend.chat(
        ChatRequest(
            model=model_id,
            messages=[ChatMessage(role=item.role, content=item.content) for item in payload.messages],
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
            stream=payload.stream,
        )
    )
    created = int(time())
    return {
        "id": response.id,
        "object": "chat.completion",
        "created": created,
        "model": response.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.content,
                },
                "finish_reason": response.finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.prompt_tokens + response.completion_tokens,
        },
    }
