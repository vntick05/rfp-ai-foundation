# Architecture Decisions

## ADR-001: Open Source Foundation Direction

### TensorRT-LLM as the preferred future inference path

Reason:

- best aligned with NVIDIA DGX-class hardware
- strongest path to future optimized local inference on this machine
- keeps the model-serving boundary compatible with a high-performance local deployment target

Alternatives still possible:

- vLLM
- llama.cpp for smaller CPU or mixed deployments
- an OpenAI-compatible proxy layer in front of another backend

### Haystack as the preferred future orchestration layer

Reason:

- mature open source orchestration framework for LLM pipelines and retrieval flows
- fits the future role of the orchestrator without forcing premature workflow design now
- supports modular pipeline growth later

Alternatives still possible:

- LangGraph
- custom FastAPI orchestration
- Temporal or Celery-backed workflow designs

### Unstructured as the preferred future parsing layer

Reason:

- strong open source fit for document ingestion pipelines
- supports complex enterprise document formats common in proposal and RFP work
- keeps parsing as a dedicated subsystem instead of mixing it into orchestration

Alternatives still possible:

- Apache Tika
- marker-based PDF pipelines
- custom parser composition for narrow document classes

### Open WebUI is intentionally deferred

Reason:

- user-facing chat or operator tooling is not required to validate the runtime foundation
- deferring it avoids premature coupling to UX assumptions
- the current API boundaries keep later Open WebUI adoption straightforward

Alternatives still possible:

- Open WebUI later
- a custom operator UI later
- direct API-first workflows without a web UI

## ADR-002: Portainer for local container management

Reason:

- provides an established open source UI for inspecting the local Docker stack immediately
- reduces pressure to build a custom operational dashboard early
- helps validate containers, logs, networks, volumes, and stack state while core platform services are still minimal

What it is not:

- not the application UI
- not an observability platform
- not a substitute for future production-grade operational controls
