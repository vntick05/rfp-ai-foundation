from dataclasses import dataclass, field
from typing import Iterator, Protocol


@dataclass(frozen=True)
class BackendDescriptor:
    name: str
    api_style: str
    gpu_capable: bool
    implemented: bool
    supports_chat: bool
    supports_streaming: bool
    status: str


@dataclass(frozen=True)
class ModelCard:
    id: str
    object: str = "model"
    owned_by: str = "local-foundation"
    ready: bool = False
    backend: str = "unknown"
    runtime_mode: str = "unknown"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BackendReadiness:
    ready: bool
    detail: str


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None
    temperature: float | None
    stream: bool


@dataclass(frozen=True)
class ChatResponse:
    id: str
    model: str
    content: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int


class ModelBackend(Protocol):
    def descriptor(self) -> BackendDescriptor:
        ...

    def readiness(self) -> BackendReadiness:
        ...

    def list_models(self) -> list[ModelCard]:
        ...

    def chat(self, request: ChatRequest) -> ChatResponse:
        ...

    def chat_stream(self, request: ChatRequest) -> Iterator[bytes]:
        ...
