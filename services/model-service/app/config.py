from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    model_service_backend: str = "mock"
    model_service_host: str = "0.0.0.0"
    model_service_port: int = 8011
    model_service_config_path: str = "/app/configs/model-service.yaml"
    model_service_model_id: str | None = None
    model_service_model_path: str | None = None
    model_service_runtime_mode: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ServiceSection(BaseModel):
    name: str = "model-service"
    default_backend: str = "mock"
    api_compatibility: str = "openai-like"


class ModelSection(BaseModel):
    id: str = "mock-gpt"
    path: str | None = None
    runtime_mode: str = "development"
    ready_on_startup: bool = True


class TensorRTLLMSection(BaseModel):
    enabled: bool = False
    engine_path: str | None = None
    tokenizer_path: str | None = None
    max_batch_size: int | None = Field(default=None, ge=1)
    notes: str = ""


class BackendOptionSection(BaseModel):
    enabled: bool = False
    notes: str = ""


class BackendsSection(BaseModel):
    mock: BackendOptionSection = Field(default_factory=lambda: BackendOptionSection(enabled=True))
    tensorrt_llm: TensorRTLLMSection = Field(default_factory=TensorRTLLMSection)
    vllm: BackendOptionSection = Field(default_factory=BackendOptionSection)


class AppConfig(BaseModel):
    service: ServiceSection = Field(default_factory=ServiceSection)
    model: ModelSection = Field(default_factory=ModelSection)
    backends: BackendsSection = Field(default_factory=BackendsSection)


def load_service_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache
def get_app_config() -> AppConfig:
    settings = get_settings()
    raw_config = load_service_config(settings.model_service_config_path)
    config = AppConfig.model_validate(raw_config)

    model_path = settings.model_service_model_path or config.model.path
    runtime_mode = settings.model_service_runtime_mode or config.model.runtime_mode
    model_id = settings.model_service_model_id or config.model.id

    config.model = config.model.model_copy(
        update={
            "id": model_id,
            "path": model_path,
            "runtime_mode": runtime_mode,
        }
    )
    config.service = config.service.model_copy(
        update={"default_backend": settings.model_service_backend}
    )

    if config.backends.tensorrt_llm.engine_path is None and model_path:
        config.backends.tensorrt_llm = config.backends.tensorrt_llm.model_copy(
            update={"engine_path": model_path}
        )

    return config


def model_path_exists(config: AppConfig) -> bool:
    if not config.model.path:
        return False
    return Path(config.model.path).exists()


@lru_cache
def get_settings() -> Settings:
    return Settings()
