# Checkpoints

## Checkpoint 1: Container Foundation

Definition:

- fresh monorepo created
- base Docker Compose stack defined
- GPU override defined for `model-service`
- `model-service` health endpoint available
- `orchestrator-api` health endpoint available
- Postgres named-volume persistence and init hook configured
- local scripts, Makefile, and docs added

Files created in this checkpoint:

- root repo metadata and env templates
- compose files
- service scaffolds under `services/`
- Postgres init under `infra/postgres/init/`
- operational scripts under `scripts/`
- architecture and local development docs under `docs/`

Verify locally:

1. `cp .env.example .env`
2. `make up`
3. `curl http://localhost:18010/healthz`
4. `curl http://localhost:18011/healthz`
5. `docker compose ps`
6. Optional DGX check: `make up-gpu`

Intentionally not built yet:

- inference implementation
- Haystack pipelines
- document parsing
- agent runtime
- UI
- RAG
- business workflows

Recommended commit message:

```text
chore: initialize local container foundation for RFP AI platform
```

## Checkpoint 2: Portainer Integration

Definition:

- Portainer CE added to the local compose stack
- Portainer persistent volume configured
- local management UI exposed on a dedicated port
- docs updated for local operational workflow and security assumptions

Verify locally:

1. `make up`
2. `make ps`
3. `make portainer-url`
4. Open `https://localhost:19443`
5. Create the initial Portainer admin user
6. Confirm the local Docker environment is visible
7. Inspect the `rfp-ai-foundation` containers, volumes, and network

Intentionally still not built:

- custom admin UI
- observability stack beyond Portainer
- application features
- agents
- parsing
- RAG

Recommended commit message:

```text
chore: add portainer for local container management
```

## Checkpoint 3: Portainer Save Point And Desktop Launcher

Definition:

- Portainer integration committed as a clean save point
- desktop launcher script added to start the local stack with the repo workflow
- desktop entry template stored in the repo and installed to the local desktop

Verify locally:

1. Double-click the desktop launcher
2. Confirm a terminal opens in the project directory
3. Confirm `make up` completes
4. Confirm `make ps` shows the four foundation services
5. Open Portainer at `https://localhost:19443`

Intentionally still not built:

- application UI
- parsing
- inference features
- agents
- workflow logic

Recommended commit message:

```text
chore: add portainer save point and desktop launcher
```

## Checkpoint 4: Model-Service API Boundary

Definition:

- `model-service` exposes a real backend-driven `GET /v1/models`
- `model-service` exposes a minimal `POST /v1/chat/completions`
- `mock` backend is implemented for deterministic smoke tests
- TensorRT-LLM adapter structure exists but remains explicitly not ready
- config expresses backend, model id, model path, and runtime mode

Verify locally:

1. `make up`
2. `curl http://localhost:18011/healthz`
3. `curl http://localhost:18011/readyz`
4. `curl http://localhost:18011/v1/models`
5. Send a `POST /v1/chat/completions` request using `mock-gpt`
6. Optional GPU shape check: `make up-gpu`

Intentionally still not built:

- actual TensorRT-LLM execution
- vLLM execution
- streaming inference
- model download/bootstrap automation
- orchestration workflows
- agents
- parsing

Recommended commit message:

```text
feat: implement model-service API boundary with swappable backend adapters
```

## Checkpoint 5: TensorRT-LLM Integration Path

Definition:

- `model-service` supports `tensorrt_llm` as a real config-driven backend option
- TensorRT-LLM readiness reflects upstream server or artifact availability honestly
- target model is explicitly `nvidia/Llama-3.3-70B-Instruct-NVFP4`
- `model-service` can proxy `GET /v1/models` and `POST /v1/chat/completions` to a local `trtllm-serve` endpoint when available
- repo-managed TensorRT-LLM sidecar added with persistent Hugging Face cache
- end-to-end inference verified through `model-service`

Verify locally:

1. `make up-trtllm`
2. `curl http://localhost:18011/readyz`
3. `curl http://localhost:18011/v1/models`
4. Send `POST /v1/chat/completions` for `nvidia/Llama-3.3-70B-Instruct-NVFP4`
5. Confirm the response returns from the TensorRT-LLM backend

Known gaps in this checkpoint:

- no embedded TensorRT-LLM runtime in the `model-service` container
- current path is sidecar proxy mode rather than embedded engine mode
- first startup is heavy because model download and warmup happen inside the sidecar
- developer-friendly warm cache/bootstrap automation is still minimal

Recommended commit message:

```text
feat: add working tensorrt-llm sidecar integration for model-service
```
