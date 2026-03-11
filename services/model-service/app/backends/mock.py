from uuid import uuid4

from app.backends.base import (
    BackendDescriptor,
    BackendReadiness,
    ChatRequest,
    ChatResponse,
    ModelBackend,
    ModelCard,
)
from app.config import AppConfig


class MockBackend(ModelBackend):
    def __init__(self, config: AppConfig):
        self._config = config

    def descriptor(self) -> BackendDescriptor:
        return BackendDescriptor(
            name="mock",
            api_style=self._config.service.api_compatibility,
            gpu_capable=False,
            implemented=True,
            supports_chat=True,
            supports_streaming=False,
            status="ready",
        )

    def readiness(self) -> BackendReadiness:
        return BackendReadiness(
            ready=True,
            detail="mock backend initialized for local service smoke tests",
        )

    def list_models(self) -> list[ModelCard]:
        model = self._config.model
        return [
            ModelCard(
                id=model.id,
                ready=True,
                backend="mock",
                runtime_mode=model.runtime_mode,
                metadata={
                    "provider": "mock",
                    "model_path": model.path or "",
                },
            )
        ]

    def chat(self, request: ChatRequest) -> ChatResponse:
        last_user_message = ""
        for message in reversed(request.messages):
            if message.role == "user":
                last_user_message = message.content.strip()
                break

        if not last_user_message:
            last_user_message = "No user message provided."

        content = (
            f"[mock-backend:{self._config.model.id}] "
            f"Received: {last_user_message}"
        )
        prompt_tokens = sum(len(message.content.split()) for message in request.messages)
        completion_tokens = len(content.split())
        return ChatResponse(
            id=f"chatcmpl-{uuid4().hex}",
            model=request.model,
            content=content,
            finish_reason="stop",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
