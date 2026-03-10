#!/usr/bin/env bash
set -euo pipefail

echo "Checking docker compose configuration"
docker compose -f docker-compose.yml config >/dev/null
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config >/dev/null

echo "Checking Python service syntax"
python3 -m py_compile \
  services/model-service/app/*.py \
  services/model-service/app/backends/*.py \
  services/orchestrator-api/app/*.py

echo "Foundation checks passed"
