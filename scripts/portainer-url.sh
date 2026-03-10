#!/usr/bin/env bash
set -euo pipefail

port="${PORTAINER_PORT:-19443}"
echo "Portainer UI: https://localhost:${port}"
echo "First access will require creating the local Portainer admin user."
