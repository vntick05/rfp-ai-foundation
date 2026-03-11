# Local Development

## Prerequisites

- Docker Engine with Compose v2
- NVIDIA Container Toolkit installed on the DGX Spark for GPU-enabled runs
- a working NVIDIA driver stack on the host

Suggested host validation:

```bash
docker compose version
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## Environment Setup

```bash
cd /home/admin/rfp-ai-foundation
cp .env.example .env
```

Review:

- exposed ports
- Postgres credentials
- compose project name
- Portainer UI port
- model-service backend, model id, and model path

## Running the Stack

Base stack:

```bash
make up
```

GPU-enabled stack:

```bash
make up-gpu
```

Portainer runs as part of the normal stack. It is a local operator tool for:

- viewing containers and stack status
- reading container logs
- inspecting volumes and networks
- confirming what is running without building a custom UI

Desktop launcher:

- a launcher template is stored at `configs/desktop/rfp-ai-foundation.desktop`
- the local desktop icon can start the stack in a terminal by running `scripts/start-foundation.sh`

## Basic Validation

```bash
curl http://localhost:18010/healthz
curl http://localhost:18010/readyz
curl http://localhost:18011/healthz
curl http://localhost:18011/readyz
curl http://localhost:18011/v1/models
docker compose ps
make portainer-url
```

Then open `https://localhost:19443`.

Minimal model-service chat smoke test:

```bash
curl -sS http://localhost:18011/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "mock-gpt",
    "messages": [{"role": "user", "content": "Return a short readiness summary."}]
  }'
```

## First-Time Portainer Setup

1. Open `https://localhost:19443`
2. Accept the local self-signed certificate warning in the browser
3. Create the initial Portainer admin user
4. Select the local Docker environment when prompted
5. Open the `Containers`, `Volumes`, `Networks`, and `Stacks` views

## Local Security Assumptions

- Portainer is added for local development only
- the UI is exposed on the local machine and should not be published to untrusted networks
- Portainer stores its state in the Docker volume `rfp-ai-foundation_portainer-data`
- Portainer has Docker socket access so it can inspect and manage the local stack
- this is intentionally convenient for local development and should be revisited before any shared or remote deployment

## Shutdown

```bash
make down
```

Postgres persistence is stored in the Docker volume `rfp-ai-foundation_postgres-data`.
Portainer persistence is stored in the Docker volume `rfp-ai-foundation_portainer-data`.

## Model-Service Notes

Implemented now:

- `mock` backend with deterministic responses for API smoke tests
- backend registry and readiness reporting
- `GET /v1/models`
- `POST /v1/chat/completions`

Not implemented yet:

- TensorRT-LLM runtime execution
- vLLM runtime execution
- streaming completions
- production model loading and caching policy
- request authentication and quotas

## Notes on Future TensorRT-LLM Support

The current `model-service` container is now a real service boundary with only the `mock` backend implemented. Later TensorRT-LLM adoption should be added behind the existing interface, likely by:

- introducing a backend adapter inside `services/model-service`
- switching the base image to a CUDA and TensorRT-compatible runtime
- mounting model artifacts from a dedicated local model cache
- preserving the external health and inference contract for upstream callers
