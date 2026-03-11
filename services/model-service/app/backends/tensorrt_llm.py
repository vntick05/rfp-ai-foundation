import json
from typing import Iterator
from urllib import error, request as urllib_request

from app.backends.base import (
    BackendDescriptor,
    BackendReadiness,
    ChatRequest,
    ChatResponse,
    ModelBackend,
    ModelCard,
)
from app.config import AppConfig, path_exists


class TensorRTLLMBackend(ModelBackend):
    def __init__(self, config: AppConfig):
        self._config = config
        self._runtime = config.backends.tensorrt_llm

    def descriptor(self) -> BackendDescriptor:
        ready = self.readiness().ready
        return BackendDescriptor(
            name="tensorrt_llm",
            api_style=self._config.service.api_compatibility,
            gpu_capable=True,
            implemented=True,
            supports_chat=True,
            supports_streaming=True,
            status="ready" if ready else "not_ready",
        )

    def readiness(self) -> BackendReadiness:
        if self._runtime.mode == "engine":
            if not self._runtime.engine_path:
                return BackendReadiness(
                    ready=False,
                    detail="TensorRT-LLM engine mode requires engine_path",
                )
            if not path_exists(self._runtime.engine_path):
                return BackendReadiness(
                    ready=False,
                    detail=f"TensorRT-LLM engine path not found: {self._runtime.engine_path}",
                )
            if not self._runtime.tokenizer_path:
                return BackendReadiness(
                    ready=False,
                    detail="TensorRT-LLM engine mode requires tokenizer_path",
                )
            if not path_exists(self._runtime.tokenizer_path):
                return BackendReadiness(
                    ready=False,
                    detail=f"TensorRT-LLM tokenizer path not found: {self._runtime.tokenizer_path}",
                )
            return BackendReadiness(
                ready=False,
                detail=(
                    "TensorRT-LLM engine artifacts are configured, but embedded runtime "
                    "execution is not implemented inside model-service; run trtllm-serve "
                    "and use proxy mode for this checkpoint"
                ),
            )

        if not self._runtime.serve_base_url:
            return BackendReadiness(
                ready=False,
                detail="TensorRT-LLM proxy mode requires serve_base_url",
            )

        try:
            self._request_json("/health")
        except RuntimeError as exc:
            return BackendReadiness(ready=False, detail=str(exc))

        try:
            models_payload = self._request_json("/v1/models")
        except RuntimeError as exc:
            return BackendReadiness(ready=False, detail=str(exc))

        model_ids = {
            item.get("id", "")
            for item in models_payload.get("data", [])
            if isinstance(item, dict)
        }
        if self._runtime.model_id not in model_ids:
            return BackendReadiness(
                ready=False,
                detail=(
                    "TensorRT-LLM server is reachable, but the expected model is not "
                    f"advertised: {self._runtime.model_id}"
                ),
            )

        return BackendReadiness(
            ready=True,
            detail=(
                "TensorRT-LLM proxy backend connected to OpenAI-compatible "
                f"server at {self._runtime.serve_base_url}"
            ),
        )

    def list_models(self) -> list[ModelCard]:
        readiness = self.readiness()
        if readiness.ready:
            payload = self._request_json("/v1/models")
            cards: list[ModelCard] = []
            for item in payload.get("data", []):
                if not isinstance(item, dict):
                    continue
                cards.append(
                    ModelCard(
                        id=item.get("id", self._runtime.model_id),
                        ready=True,
                        backend="tensorrt_llm",
                        runtime_mode=self._runtime.mode,
                        metadata={
                            "provider": "tensorrt_llm",
                            "serve_base_url": self._runtime.serve_base_url or "",
                            "engine_path": self._runtime.engine_path or "",
                            "tokenizer_path": self._runtime.tokenizer_path or "",
                        },
                    )
                )
            if cards:
                return cards

        return [
            ModelCard(
                id=self._runtime.model_id,
                ready=readiness.ready,
                backend="tensorrt_llm",
                runtime_mode=self._runtime.mode,
                metadata={
                    "provider": "tensorrt_llm",
                    "serve_base_url": self._runtime.serve_base_url or "",
                    "engine_path": self._runtime.engine_path or "",
                    "tokenizer_path": self._runtime.tokenizer_path or "",
                },
            )
        ]

    def chat(self, request: ChatRequest) -> ChatResponse:
        readiness = self.readiness()
        if not readiness.ready:
            raise NotImplementedError(readiness.detail)

        payload = self._request_json(
            "/v1/chat/completions",
            method="POST",
            payload={
                "model": request.model,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in request.messages
                ],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": False,
            },
        )
        choice = payload.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = payload.get("usage", {})
        return ChatResponse(
            id=payload.get("id", "chatcmpl-trtllm"),
            model=payload.get("model", request.model),
            content=message.get("content", ""),
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )

    def chat_stream(self, request: ChatRequest) -> Iterator[bytes]:
        readiness = self.readiness()
        if not readiness.ready:
            raise NotImplementedError(readiness.detail)

        yield from self._request_stream(
            "/v1/chat/completions",
            payload={
                "model": request.model,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in request.messages
                ],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": True,
            },
        )

    def _request_json(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if not self._runtime.serve_base_url:
            raise RuntimeError("TensorRT-LLM serve_base_url is not configured")

        url = f"{self._runtime.serve_base_url.rstrip('/')}{path}"
        data: bytes | None = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib_request.Request(url=url, data=data, method=method, headers=headers)
        try:
            with urllib_request.urlopen(req, timeout=self._runtime.request_timeout_seconds) as response:
                body = response.read().decode("utf-8")
                if not body:
                    return {}
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    return parsed
                raise RuntimeError(f"Unexpected JSON payload from TensorRT-LLM server: {url}")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"TensorRT-LLM server returned HTTP {exc.code} for {url}: {body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"TensorRT-LLM server is not reachable at {url}: {exc.reason}"
            ) from exc

    def _request_stream(
        self,
        path: str,
        payload: dict[str, object],
    ) -> Iterator[bytes]:
        if not self._runtime.serve_base_url:
            raise RuntimeError("TensorRT-LLM serve_base_url is not configured")

        url = f"{self._runtime.serve_base_url.rstrip('/')}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            url=url,
            data=data,
            method="POST",
            headers={
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=self._runtime.request_timeout_seconds) as response:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    yield line
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"TensorRT-LLM server returned HTTP {exc.code} for {url}: {body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"TensorRT-LLM server is not reachable at {url}: {exc.reason}"
            ) from exc
