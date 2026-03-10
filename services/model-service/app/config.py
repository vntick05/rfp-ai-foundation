from functools import lru_cache
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    model_service_backend: str = "mock"
    model_service_host: str = "0.0.0.0"
    model_service_port: int = 8011
    model_service_config_path: str = "/app/configs/model-service.yaml"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def load_service_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
