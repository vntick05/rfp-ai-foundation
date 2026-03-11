from app.backends.base import (
    BackendDescriptor,
    BackendReadiness,
    ChatRequest,
    ChatResponse,
    ModelBackend,
    ModelCard,
)
from app.config import AppConfig


class TensorRTLLMBackend(ModelBackend):
    def __init__(self, config: AppConfig):
        self._config = config

    def descriptor(self) -> BackendDescriptor:
        ready = self.readiness().ready
        return BackendDescriptor(
            name="tensorrt_llm",
            api_style=self._config.service.api_compatibility,
            gpu_capable=True,
            implemented=False,
            supports_chat=False,
            supports_streaming=False,
            status="ready" if ready else "not_ready",
        )

    def readiness(self) -> BackendReadiness:
        model_path = self._config.model.path
        if not model_path:
            return BackendReadiness(
                ready=False,
                detail="TensorRT-LLM adapter configured without a model engine path",
            )
        return BackendReadiness(
            ready=False,
            detail=(
                "TensorRT-LLM adapter structure is present, but runtime wiring is not "
                "implemented in this checkpoint"
            ),
        )

    def list_models(self) -> list[ModelCard]:
        readiness = self.readiness()
        return [
            ModelCard(
                id=self._config.model.id,
                ready=readiness.ready,
                backend="tensorrt_llm",
                runtime_mode=self._config.model.runtime_mode,
                metadata={
                    "provider": "tensorrt_llm",
                    "model_path": self._config.model.path or "",
                },
            )
        ]

    def chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError(self.readiness().detail)
