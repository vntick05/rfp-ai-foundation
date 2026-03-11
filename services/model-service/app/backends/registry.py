from app.backends.base import ModelBackend
from app.backends.mock import MockBackend
from app.backends.tensorrt_llm import TensorRTLLMBackend
from app.config import AppConfig


def create_backend(config: AppConfig) -> ModelBackend:
    backend_name = config.service.default_backend
    if backend_name == "mock":
        return MockBackend(config)
    if backend_name == "tensorrt_llm":
        return TensorRTLLMBackend(config)
    raise ValueError(f"Unsupported model-service backend: {backend_name}")
