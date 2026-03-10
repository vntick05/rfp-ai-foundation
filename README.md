# RFP AI Foundation

Local-first, containerized foundation for a proposal and RFP analysis platform on NVIDIA DGX-class hardware.

This repository intentionally stops at the architectural foundation:

- Docker-based local stack
- Portainer CE for local container inspection and management
- GPU-ready model service boundary
- Minimal FastAPI orchestrator API
- Postgres foundation with persistent storage
- Documentation and checkpoint discipline

Not built yet:

- proposal analysis logic
- agents
- parsing
- RAG
- custom UI
- workflow implementations

## Repo Layout

```text
rfp-ai-foundation/
├── apps/
├── configs/
├── data/
├── docs/
├── infra/
├── scripts/
├── services/
└── tests/
```

## Quick Start

1. Copy environment defaults:

```bash
cp .env.example .env
```

2. Review ports and credentials in `.env`.

3. Start the base stack:

```bash
make up
```

4. Start with GPU runtime enabled for the future model-service path:

```bash
make up-gpu
```

5. Check health:

```bash
make ps
curl http://localhost:18010/healthz
curl http://localhost:18011/healthz
make portainer-url
```

6. Stop services:

```bash
make down
```

Portainer is available at `https://localhost:19443` by default. On first access, create the local admin account and attach the local Docker environment.
For desktop convenience, a launcher template is stored in `configs/desktop/` and a local desktop icon can start the stack in a terminal window.

See [docs/local-development.md](/home/admin/rfp-ai-foundation/docs/local-development.md) and [docs/checkpoints.md](/home/admin/rfp-ai-foundation/docs/checkpoints.md) before extending the stack.
