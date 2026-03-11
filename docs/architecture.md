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

What is real now:

- a working `mock` backend for service-level smoke tests
- backend registry and adapter structure
- explicit TensorRT-LLM adapter placeholder with honest not-ready behavior

What is still scaffolded:

- TensorRT-LLM runtime wiring
- vLLM runtime wiring
- model artifact loading beyond config surfaces
- streaming responses

Planned future backend options:

- TensorRT-LLM as the preferred NVIDIA path
- vLLM where API compatibility or ecosystem tooling is more important
- an OpenAI-compatible local facade when downstream tooling expects it

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
