import json
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
            supports_streaming=True,
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

    def chat_stream(self, request: ChatRequest):
        response = self.chat(request)
        chunk_id = response.id
        yield self._sse_chunk(
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "model": response.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }
                ],
            }
        )
        yield self._sse_chunk(
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "model": response.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": response.content},
                        "finish_reason": None,
                    }
                ],
            }
        )
        yield self._sse_chunk(
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "model": response.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": response.finish_reason,
                    }
                ],
            }
        )
        yield b"data: [DONE]\n\n"

    def _sse_chunk(self, payload: dict[str, object]) -> bytes:
        return f"data: {json.dumps(payload)}\n\n".encode("utf-8")
