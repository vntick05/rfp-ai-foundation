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
- model-service backend, model id, model path, and runtime request settings

## Running the Stack

Base stack:

```bash
make up
```

GPU-enabled stack:

```bash
make up-gpu
```

GPU-enabled stack with TensorRT-LLM sidecar:

```bash
make up-trtllm
```

This command:

- starts the TensorRT-LLM sidecar
- forces `model-service` onto the `tensorrt_llm` backend
- keeps the rest of the stack unchanged

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

Internal container-to-container validation:

```bash
docker compose exec orchestrator-api wget -q -O - http://model-service:8011/readyz
docker compose exec orchestrator-api wget -q -O - http://model-service:8011/v1/models
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
- streaming `POST /v1/chat/completions` when `stream=true`
- structured JSON request logs
- request ID propagation with `X-Request-ID`
- request timeout responses and bounded in-flight request handling
- TensorRT-LLM proxy integration path for `nvidia/Llama-3.3-70B-Instruct-NVFP4`
- TensorRT-LLM engine-mode lifecycle wiring inside `model-service`

Not implemented yet:

- vLLM runtime execution
- production model loading and caching policy
- request authentication and quotas

## Internal Service Calling Pattern

For other containers in the same compose project:

- use `http://model-service:8011`
- do not use `localhost:18011`
- treat host port `18011` as a host-machine convenience only

Recommended request headers for internal callers:

- `Content-Type: application/json`
- `X-Request-ID: <caller-generated-id>` when a caller wants stable trace correlation across services

Readiness semantics:

- `GET /healthz` means the FastAPI process is alive
- `GET /readyz` means the selected backend is actually usable right now
- if the selected backend is unavailable, `GET /readyz` returns `503`

Current reliability controls:

- request timeout is configurable with `MODEL_SERVICE_REQUEST_TIMEOUT_SECONDS`
- max in-flight requests is configurable with `MODEL_SERVICE_MAX_CONCURRENT_REQUESTS`
- overload responses use `MODEL_SERVICE_OVERLOAD_STATUS_CODE`
- successful and failed requests log timestamp, request ID, endpoint, backend, model ID, duration, and status

## TensorRT-LLM Prerequisites For This Checkpoint

Target model:

- `nvidia/Llama-3.3-70B-Instruct-NVFP4`

This checkpoint expects one of the following to exist before TensorRT-LLM can become ready:

1. A local `trtllm-serve` process or container exposing an OpenAI-compatible API
2. A future embedded runtime implementation with prebuilt engine artifacts and tokenizer files

Configured defaults:

- mode: `proxy`
- upstream URL from inside `model-service`: `http://tensorrt-llm:8000`
- expected engine path: `/models/tensorrt-llm/llama-3.3-70b-instruct-nvfp4`
- expected tokenizer path: `/models/tensorrt-llm/llama-3.3-70b-instruct-nvfp4`
- TensorRT-LLM runtime image: `nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc3`
- Hugging Face cache mount: `./data/cache/huggingface`

What is actually verified in this repository now:

- `model-service` can speak to the repo-managed TensorRT-LLM sidecar
- readiness becomes degraded with a clear reason if the endpoint or artifacts are missing
- end-to-end inference succeeded for `nvidia/Llama-3.3-70B-Instruct-NVFP4`
- engine mode reports exact artifact/runtime blockers instead of pretending to be usable

What is not verified yet on this machine:

- long-run operational stability under repeated requests
- optimized TensorRT engine-mode serving inside `model-service`
- startup/warmup time tuning for developer ergonomics

## TensorRT-LLM Engine Mode

Engine mode now expects:

- prebuilt TensorRT engine artifacts at `/models/tensorrt-llm/llama-3.3-70b-instruct-nvfp4`
- tokenizer assets at `/models/tensorrt-llm/llama-3.3-70b-instruct-nvfp4`
- a `model-service` image that includes `trtllm-serve`

Relevant config:

- `MODEL_SERVICE_TENSORRT_LLM_MODE=engine`
- `MODEL_SERVICE_TENSORRT_LLM_ENGINE_PATH=/models/tensorrt-llm/llama-3.3-70b-instruct-nvfp4`
- `MODEL_SERVICE_TENSORRT_LLM_TOKENIZER_PATH=/models/tensorrt-llm/llama-3.3-70b-instruct-nvfp4`
- `MODEL_SERVICE_TENSORRT_LLM_EMBEDDED_HOST=127.0.0.1`
- `MODEL_SERVICE_TENSORRT_LLM_EMBEDDED_PORT=8020`
- `MODEL_SERVICE_TENSORRT_LLM_EMBEDDED_BACKEND=tensorrt`
- `MODEL_SERVICE_TENSORRT_LLM_EXECUTABLE=trtllm-serve`
- `MODEL_SERVICE_BASE_IMAGE=nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc3` when building a TensorRT-capable `model-service` image

What is in scope in this checkpoint:

- `model-service` can manage a local embedded `trtllm-serve` process for engine mode
- readiness and failure messages are explicit about missing artifacts or runtime binaries

What is not in scope in this checkpoint:

- building the TensorRT engine itself
- guaranteeing a working engine-mode smoke test without those artifacts

Verified TensorRT-LLM verification flow:

```bash
cd /home/admin/rfp-ai-foundation
cp .env.example .env
make up-trtllm
curl http://localhost:18011/readyz
curl http://localhost:18011/v1/models
curl -sS http://localhost:18011/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "nvidia/Llama-3.3-70B-Instruct-NVFP4",
    "messages": [{"role": "user", "content": "Reply with exactly: model-service healthy"}],
    "max_tokens": 16,
    "temperature": 0
  }'
```

TensorRT-LLM streaming verification flow:

```bash
docker compose exec orchestrator-api python -c "import json, urllib.request; req=urllib.request.Request('http://model-service:8011/v1/chat/completions', data=json.dumps({'model':'nvidia/Llama-3.3-70B-Instruct-NVFP4','messages':[{'role':'user','content':'Reply with exactly: streaming works'}],'max_tokens':16,'temperature':0,'stream':True}).encode(), headers={'Content-Type':'application/json','X-Request-ID':'trt-stream-1'}); resp=urllib.request.urlopen(req, timeout=120); print(resp.read().decode())"
```

## Notes on Future TensorRT-LLM Support

The current `model-service` container is now a real service boundary with `mock` implemented and TensorRT-LLM proxy integration added. Later deeper TensorRT-LLM adoption should be added behind the existing interface, likely by:

- introducing a backend adapter inside `services/model-service`
- deciding whether to stay with a sidecar `trtllm-serve` runtime or move to an embedded CUDA and TensorRT-compatible runtime
- mounting model artifacts from a dedicated local model cache
- preserving the external health and inference contract for upstream callers
