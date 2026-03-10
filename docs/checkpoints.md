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
