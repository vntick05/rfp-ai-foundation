from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

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
    model_service_request_timeout_seconds: float | None = None
    model_service_max_concurrent_requests: int | None = None
    model_service_overload_status_code: int | None = None
    model_service_request_id_header: str | None = None
    model_service_model_id: str | None = None
    model_service_model_path: str | None = None
    model_service_runtime_mode: str | None = None
    model_service_tensorrt_llm_mode: str | None = None
    model_service_tensorrt_llm_base_url: str | None = None
    model_service_tensorrt_llm_model_id: str | None = None
    model_service_tensorrt_llm_engine_path: str | None = None
    model_service_tensorrt_llm_tokenizer_path: str | None = None
    model_service_tensorrt_llm_request_timeout_seconds: float | None = None
    model_service_tensorrt_llm_checkpoint_path: str | None = None
    model_service_tensorrt_llm_hf_cache_dir: str | None = None
    model_service_tensorrt_llm_max_batch_size: int | None = None
    model_service_tensorrt_llm_max_num_tokens: int | None = None
    model_service_tensorrt_llm_max_seq_len: int | None = None
    model_service_tensorrt_llm_embedded_host: str | None = None
    model_service_tensorrt_llm_embedded_port: int | None = None
    model_service_tensorrt_llm_embedded_backend: str | None = None
    model_service_tensorrt_llm_server_start_timeout_seconds: float | None = None
    model_service_tensorrt_llm_executable: str | None = None

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


class RuntimeSection(BaseModel):
    request_timeout_seconds: float = Field(default=60.0, gt=0)
    max_concurrent_requests: int = Field(default=8, ge=1)
    overload_status_code: int = Field(default=503, ge=429, le=503)
    request_id_header: str = "X-Request-ID"


class TensorRTLLMSection(BaseModel):
    enabled: bool = False
    mode: Literal["proxy", "engine"] = "proxy"
    model_id: str = "nvidia/Llama-3.3-70B-Instruct-NVFP4"
    serve_base_url: str | None = None
    engine_path: str | None = None
    checkpoint_path: str | None = None
    hf_cache_dir: str = "/root/.cache/huggingface"
    tokenizer_path: str | None = None
    embedded_host: str = "127.0.0.1"
    embedded_port: int = Field(default=8020, ge=1, le=65535)
    embedded_backend: Literal["pytorch", "tensorrt"] = "tensorrt"
    server_start_timeout_seconds: float = Field(default=180.0, gt=0)
    executable: str = "trtllm-serve"
    max_batch_size: int | None = Field(default=1, ge=1)
    max_num_tokens: int | None = Field(default=2048, ge=1)
    max_seq_len: int | None = Field(default=8192, ge=1)
    request_timeout_seconds: float = Field(default=30.0, gt=0)
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
    runtime: RuntimeSection = Field(default_factory=RuntimeSection)
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
    config.runtime = config.runtime.model_copy(
        update={
            "request_timeout_seconds": (
                settings.model_service_request_timeout_seconds
                or config.runtime.request_timeout_seconds
            ),
            "max_concurrent_requests": (
                settings.model_service_max_concurrent_requests
                or config.runtime.max_concurrent_requests
            ),
            "overload_status_code": (
                settings.model_service_overload_status_code
                or config.runtime.overload_status_code
            ),
            "request_id_header": (
                settings.model_service_request_id_header
                or config.runtime.request_id_header
            ),
        }
    )

    tensorrt_model_id = (
        settings.model_service_tensorrt_llm_model_id
        or config.backends.tensorrt_llm.model_id
    )
    tensorrt_engine_path = (
        settings.model_service_tensorrt_llm_engine_path
        or config.backends.tensorrt_llm.engine_path
    )
    tensorrt_checkpoint_path = (
        settings.model_service_tensorrt_llm_checkpoint_path
        or config.backends.tensorrt_llm.checkpoint_path
    )
    tensorrt_hf_cache_dir = (
        settings.model_service_tensorrt_llm_hf_cache_dir
        or config.backends.tensorrt_llm.hf_cache_dir
    )
    tensorrt_tokenizer_path = (
        settings.model_service_tensorrt_llm_tokenizer_path
        or config.backends.tensorrt_llm.tokenizer_path
    )
    tensorrt_mode = (
        settings.model_service_tensorrt_llm_mode
        or config.backends.tensorrt_llm.mode
    )
    tensorrt_base_url = (
        settings.model_service_tensorrt_llm_base_url
        or config.backends.tensorrt_llm.serve_base_url
    )
    tensorrt_timeout = (
        settings.model_service_tensorrt_llm_request_timeout_seconds
        or config.backends.tensorrt_llm.request_timeout_seconds
    )
    tensorrt_max_batch_size = (
        settings.model_service_tensorrt_llm_max_batch_size
        or config.backends.tensorrt_llm.max_batch_size
    )
    tensorrt_max_num_tokens = (
        settings.model_service_tensorrt_llm_max_num_tokens
        or config.backends.tensorrt_llm.max_num_tokens
    )
    tensorrt_max_seq_len = (
        settings.model_service_tensorrt_llm_max_seq_len
        or config.backends.tensorrt_llm.max_seq_len
    )
    tensorrt_embedded_host = (
        settings.model_service_tensorrt_llm_embedded_host
        or config.backends.tensorrt_llm.embedded_host
    )
    tensorrt_embedded_port = (
        settings.model_service_tensorrt_llm_embedded_port
        or config.backends.tensorrt_llm.embedded_port
    )
    tensorrt_embedded_backend = (
        settings.model_service_tensorrt_llm_embedded_backend
        or config.backends.tensorrt_llm.embedded_backend
    )
    tensorrt_server_start_timeout = (
        settings.model_service_tensorrt_llm_server_start_timeout_seconds
        or config.backends.tensorrt_llm.server_start_timeout_seconds
    )
    tensorrt_executable = (
        settings.model_service_tensorrt_llm_executable
        or config.backends.tensorrt_llm.executable
    )

    config.backends.tensorrt_llm = config.backends.tensorrt_llm.model_copy(
        update={
            "mode": tensorrt_mode,
            "model_id": tensorrt_model_id,
            "serve_base_url": tensorrt_base_url,
            "engine_path": tensorrt_engine_path,
            "checkpoint_path": tensorrt_checkpoint_path,
            "hf_cache_dir": tensorrt_hf_cache_dir,
            "tokenizer_path": tensorrt_tokenizer_path,
            "embedded_host": tensorrt_embedded_host,
            "embedded_port": tensorrt_embedded_port,
            "embedded_backend": tensorrt_embedded_backend,
            "server_start_timeout_seconds": tensorrt_server_start_timeout,
            "executable": tensorrt_executable,
            "max_batch_size": tensorrt_max_batch_size,
            "max_num_tokens": tensorrt_max_num_tokens,
            "max_seq_len": tensorrt_max_seq_len,
            "request_timeout_seconds": tensorrt_timeout,
        }
    )

    return config


def model_path_exists(config: AppConfig) -> bool:
    if not config.model.path:
        return False
    return Path(config.model.path).exists()


def path_exists(path: str | None) -> bool:
    if not path:
        return False
    return Path(path).exists()


@lru_cache
def get_settings() -> Settings:
    return Settings()
