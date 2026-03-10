from fastapi import FastAPI

from app.backends.base import BackendDescriptor
from app.config import get_settings, load_service_config

app = FastAPI(title="model-service", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, object]:
    settings = get_settings()
    config = load_service_config(settings.model_service_config_path)
    backend = BackendDescriptor(
        name=settings.model_service_backend,
        api_style="openai-like",
        gpu_capable=True,
        implemented=settings.model_service_backend == "mock",
    )
    return {
        "status": "ready",
        "service": "model-service",
        "backend": backend.__dict__,
        "config_loaded": bool(config),
    }


@app.get("/v1/models")
def list_models() -> dict[str, object]:
    settings = get_settings()
    return {
        "object": "list",
        "data": [
            {
                "id": f"{settings.model_service_backend}-placeholder",
                "object": "model",
                "owned_by": "local-foundation",
                "ready": False,
            }
        ],
    }
