# Architecture Foundation

## Current Scope

This checkpoint establishes only the runtime foundation:

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

## Container Topology

Base compose:

- runs on a standard Docker host
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
