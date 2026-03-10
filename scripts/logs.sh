#!/usr/bin/env bash
set -euo pipefail

docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f --tail=100 "$@"
