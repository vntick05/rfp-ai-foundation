from contextlib import asynccontextmanager
from time import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.backends.base import ChatMessage, ChatRequest
from app.backends.registry import create_backend
from app.config import get_app_config, get_settings, model_path_exists
from app.schemas import ChatCompletionRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_app_config()
    app.state.backend = create_backend(config)
    yield


app = FastAPI(title="model-service", version="0.2.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> JSONResponse:
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

    if primary_model is not None:
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
            "detail": readiness.detail,
        },
    )


@app.get("/v1/models")
def list_models() -> dict[str, object]:
    backend = app.state.backend
    return {
        "object": "list",
        "data": [model.__dict__ for model in backend.list_models()],
    }


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest) -> dict[str, object]:
    backend = app.state.backend
    descriptor = backend.descriptor()
    readiness = backend.readiness()

    if request.stream:
        raise HTTPException(status_code=501, detail="Streaming is not implemented in this checkpoint")

    if not descriptor.supports_chat:
        raise HTTPException(status_code=501, detail=f"Backend '{descriptor.name}' does not support chat completions")

    if not readiness.ready:
        raise HTTPException(status_code=503, detail=readiness.detail)

    config = get_app_config()
    available_models = {model.id for model in backend.list_models()}
    default_model_id = next(iter(available_models), config.model.id)
    model_id = request.model or default_model_id
    if model_id not in available_models:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' is not available")

    response = backend.chat(
        ChatRequest(
            model=model_id,
            messages=[ChatMessage(role=item.role, content=item.content) for item in request.messages],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
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
