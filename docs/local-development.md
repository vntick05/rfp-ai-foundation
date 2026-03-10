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

## Running the Stack

Base stack:

```bash
make up
```

GPU-enabled stack:

```bash
make up-gpu
```

## Basic Validation

```bash
curl http://localhost:18010/healthz
curl http://localhost:18010/readyz
curl http://localhost:18011/healthz
docker compose ps
```

## Shutdown

```bash
make down
```

Postgres persistence is stored in the Docker volume `rfp-ai-foundation_postgres-data`.

## Notes on Future TensorRT-LLM Support

The current `model-service` container is only a boundary scaffold. Later TensorRT-LLM adoption should be added behind the existing service interface, likely by:

- introducing a backend adapter inside `services/model-service`
- switching the base image to a CUDA and TensorRT-compatible runtime
- mounting model artifacts from a dedicated local model cache
- preserving the external health and inference contract for upstream callers
