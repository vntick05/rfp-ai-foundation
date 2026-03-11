import json
import shutil
import subprocess
from pathlib import Path
from time import monotonic, sleep
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
        self._embedded_process: subprocess.Popen | None = None
        self._startup_error: str | None = None

    def startup(self) -> None:
        if self._runtime.mode != "engine":
            return

        self._startup_error = None
        validation_error = self._validate_engine_mode_config()
        if validation_error:
            self._startup_error = validation_error
            return

        executable = shutil.which(self._runtime.executable)
        if not executable:
            self._startup_error = (
                "TensorRT-LLM engine mode requires the "
                f"'{self._runtime.executable}' executable inside the model-service container"
            )
            return

        if self._embedded_process and self._embedded_process.poll() is None:
            return

        command = [
            executable,
            "serve",
            self._serving_model_path() or "",
            "--tokenizer",
            self._resolved_tokenizer_path() or "",
            "--backend",
            self._runtime.embedded_backend,
            "--host",
            self._runtime.embedded_host,
            "--port",
            str(self._runtime.embedded_port),
        ]
        if self._runtime.max_batch_size:
            command.extend(["--max_batch_size", str(self._runtime.max_batch_size)])
        if self._runtime.max_num_tokens:
            command.extend(["--max_num_tokens", str(self._runtime.max_num_tokens)])
        if self._runtime.max_seq_len:
            command.extend(["--max_seq_len", str(self._runtime.max_seq_len)])
        self._embedded_process = subprocess.Popen(
            command,
            stdout=None,
            stderr=None,
            text=False,
        )

        deadline = monotonic() + self._runtime.server_start_timeout_seconds
        last_error = "TensorRT-LLM embedded runtime did not report ready"
        while monotonic() < deadline:
            if self._embedded_process.poll() is not None:
                self._startup_error = (
                    "TensorRT-LLM embedded runtime exited during startup with code "
                    f"{self._embedded_process.returncode}"
                )
                return
            try:
                self._request_json("/health")
                self._startup_error = None
                return
            except RuntimeError as exc:
                last_error = str(exc)
                sleep(2)

        self._startup_error = (
            "Timed out waiting for embedded TensorRT-LLM runtime to become ready: "
            f"{last_error}"
        )

    def shutdown(self) -> None:
        if not self._embedded_process:
            return
        if self._embedded_process.poll() is None:
            self._embedded_process.terminate()
            try:
                self._embedded_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._embedded_process.kill()
                self._embedded_process.wait(timeout=5)
        self._embedded_process = None

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
            validation_error = self._validate_engine_mode_config()
            if validation_error:
                return BackendReadiness(ready=False, detail=validation_error)
            if self._startup_error:
                return BackendReadiness(ready=False, detail=self._startup_error)
            if not self._embedded_process:
                return BackendReadiness(
                    ready=False,
                    detail="TensorRT-LLM embedded runtime was not started by model-service",
                )
            if self._embedded_process.poll() is not None:
                return BackendReadiness(
                    ready=False,
                    detail=(
                        "TensorRT-LLM embedded runtime exited with code "
                        f"{self._embedded_process.returncode}"
                    ),
                )
            try:
                self._request_json("/health")
            except RuntimeError as exc:
                return BackendReadiness(ready=False, detail=str(exc))
            return BackendReadiness(
                ready=True,
                detail=(
                    "TensorRT-LLM engine backend is running inside model-service at "
                    f"{self._serving_base_url()}"
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
                            "serve_base_url": self._serving_base_url(),
                            "engine_path": self._runtime.engine_path or "",
                            "checkpoint_path": self._serving_model_path() or "",
                            "tokenizer_path": self._resolved_tokenizer_path() or "",
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
                    "serve_base_url": self._serving_base_url(),
                    "engine_path": self._runtime.engine_path or "",
                    "checkpoint_path": self._serving_model_path() or "",
                    "tokenizer_path": self._resolved_tokenizer_path() or "",
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
        base_url = self._serving_base_url()
        if not base_url:
            raise RuntimeError("TensorRT-LLM serve_base_url is not configured")

        url = f"{base_url.rstrip('/')}{path}"
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
        base_url = self._serving_base_url()
        if not base_url:
            raise RuntimeError("TensorRT-LLM serve_base_url is not configured")

        url = f"{base_url.rstrip('/')}{path}"
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

    def _serving_base_url(self) -> str | None:
        if self._runtime.mode == "engine":
            return f"http://{self._runtime.embedded_host}:{self._runtime.embedded_port}"
        return self._runtime.serve_base_url

    def _validate_engine_mode_config(self) -> str | None:
        serving_model_path = self._serving_model_path()
        if not serving_model_path:
            return (
                "TensorRT-LLM engine mode requires either prebuilt engine artifacts or "
                "a local checkpoint path in the Hugging Face cache"
            )
        if not path_exists(serving_model_path):
            return f"TensorRT-LLM model source path not found: {serving_model_path}"
        if self._runtime.engine_path and path_exists(self._runtime.engine_path):
            engine_path = Path(self._runtime.engine_path)
            if engine_path.is_dir() and not any(item.name != ".gitkeep" for item in engine_path.iterdir()):
                checkpoint_path = self._resolved_checkpoint_path()
                if not checkpoint_path:
                    return (
                        "TensorRT-LLM engine path exists but does not contain engine artifacts: "
                        f"{self._runtime.engine_path}"
                    )
        tokenizer_path_value = self._resolved_tokenizer_path()
        if not tokenizer_path_value:
            return (
                "TensorRT-LLM engine mode requires tokenizer assets, either via "
                "tokenizer_path or the local checkpoint snapshot"
            )
        if not path_exists(tokenizer_path_value):
            return f"TensorRT-LLM tokenizer path not found: {tokenizer_path_value}"
        tokenizer_path = Path(tokenizer_path_value)
        tokenizer_candidates = (
            "tokenizer.json",
            "tokenizer.model",
            "tokenizer_config.json",
        )
        if tokenizer_path.is_dir() and not any((tokenizer_path / candidate).exists() for candidate in tokenizer_candidates):
            return (
                "TensorRT-LLM tokenizer path exists but does not contain tokenizer assets: "
                f"{tokenizer_path_value}"
            )
        return None

    def _resolved_checkpoint_path(self) -> str | None:
        if self._runtime.checkpoint_path and path_exists(self._runtime.checkpoint_path):
            return self._runtime.checkpoint_path

        model_slug = self._runtime.model_id.replace("/", "--")
        refs_main_path = (
            Path(self._runtime.hf_cache_dir)
            / "hub"
            / f"models--{model_slug}"
            / "refs"
            / "main"
        )
        if not refs_main_path.exists():
            return None
        snapshot_ref = refs_main_path.read_text(encoding="utf-8").strip()
        if not snapshot_ref:
            return None
        snapshot_path = (
            Path(self._runtime.hf_cache_dir)
            / "hub"
            / f"models--{model_slug}"
            / "snapshots"
            / snapshot_ref
        )
        return str(snapshot_path) if snapshot_path.exists() else None

    def _resolved_tokenizer_path(self) -> str | None:
        if self._runtime.tokenizer_path and path_exists(self._runtime.tokenizer_path):
            tokenizer_path = Path(self._runtime.tokenizer_path)
            tokenizer_candidates = (
                "tokenizer.json",
                "tokenizer.model",
                "tokenizer_config.json",
            )
            if tokenizer_path.is_file():
                return self._runtime.tokenizer_path
            if tokenizer_path.is_dir() and any((tokenizer_path / candidate).exists() for candidate in tokenizer_candidates):
                return self._runtime.tokenizer_path
        return self._resolved_checkpoint_path()

    def _serving_model_path(self) -> str | None:
        if self._runtime.engine_path and path_exists(self._runtime.engine_path):
            engine_path = Path(self._runtime.engine_path)
            if engine_path.is_dir() and any(item.name != ".gitkeep" for item in engine_path.iterdir()):
                return self._runtime.engine_path
        return self._resolved_checkpoint_path()
