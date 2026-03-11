# Architecture Foundation

## Current Scope

This checkpoint establishes only the runtime foundation:

- `portainer` for local container visibility and stack management
- `postgres` for persistent relational storage
- `orchestrator-api` as the future coordination boundary
- `model-service` as the future local inference boundary

The stack is intentionally thin so the project can evolve without early coupling.

## Service Boundaries

### `model-service`

Purpose:

- expose a stable internal HTTP boundary for future inference
- allow backend swaps without forcing upstream service rewrites
- keep NVIDIA-specific serving concerns isolated from orchestration logic

Current implementation in this checkpoint:

- `GET /healthz` for container liveness
- `GET /readyz` for backend readiness and model/runtime reporting
- `GET /v1/models` from active backend state
- `POST /v1/chat/completions` as the minimal inference boundary
- streamed `POST /v1/chat/completions` when the active backend supports it
- structured request logging and request ID propagation for internal callers
- bounded in-flight request handling and timeout-aware error responses

What is real now:

- a working `mock` backend for service-level smoke tests
- backend registry and adapter structure
- explicit TensorRT-LLM integration path to a local `trtllm-serve` server with honest readiness behavior
- verified end-to-end TensorRT-LLM response through `model-service`
- Docker-internal access pattern via `http://model-service:8011`
- engine-mode lifecycle wiring for a local embedded `trtllm-serve` process inside `model-service`

What is still scaffolded:

- vLLM runtime wiring
- model artifact loading beyond config surfaces

What still blocks real engine mode on a fresh machine:

- no prebuilt TensorRT engine artifacts are stored in the repo
- the default `model-service` image remains `python:3.12-slim`, which does not include `trtllm-serve`
- automated engine build flow remains separate work

Planned future backend options:

- TensorRT-LLM as the preferred NVIDIA path
- vLLM where API compatibility or ecosystem tooling is more important
- an OpenAI-compatible local facade when downstream tooling expects it

Internal caller contract:

- callers inside Docker should use service naming, not published host ports
- `GET /healthz` is only a process liveness signal
- `GET /readyz` is the backend usability signal
- callers should send `X-Request-ID` if they want trace continuity in logs and future upstream services

Current TensorRT-LLM checkpoint target:

- model identifier: `nvidia/Llama-3.3-70B-Instruct-NVFP4`
- default integration mode: proxy to a repo-managed local `trtllm-serve` sidecar
- recommended DGX Spark runtime path: run `hf download "$MODEL_HANDLE"` and then `trtllm-serve "$MODEL_HANDLE"` in the sidecar, with `model-service` kept as the stable internal API boundary
- expected artifact directory for prebuilt engines: `/models/tensorrt-llm/llama-3.3-70b-instruct-nvfp4`
- engine-mode runtime image expectation: a TensorRT-capable `model-service` image such as `nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc3`

### `orchestrator-api`

Purpose:

- own external API coordination for future workflows
- encapsulate service-to-service calls
- become the clean insertion point for Haystack pipelines later

### `postgres`

Purpose:

- store future workflow state, metadata, documents, and structured analysis artifacts
- remain independent from inference runtime choices
- use a Docker-managed persistent volume in this foundation checkpoint for reliability

### `portainer`

Purpose:

- provide an open source operational UI for the local Docker environment
- inspect containers, logs, volumes, networks, and stack status while the platform is being built
- reduce the need for a custom admin UI during early platform construction

Non-goals:

- not a replacement for application UI
- not a replacement for infrastructure-as-code
- not a production control plane for remote multi-user administration

## Container Topology

Base compose:

- runs on a standard Docker host
- includes Portainer CE for local stack inspection
- keeps GPU concerns out of the default path

GPU override compose:

- adds NVIDIA runtime access only where needed
- keeps the repo portable to non-DGX environments

## Deferred Components

Not introduced in this checkpoint:

- Haystack runtime integration
- Unstructured workers
- Open WebUI
- vector databases
- queueing systems
- model download automation
