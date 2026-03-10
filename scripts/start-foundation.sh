#!/usr/bin/env bash
set -euo pipefail

repo_dir="/home/admin/rfp-ai-foundation"

cd "${repo_dir}"
gnome-terminal -- bash -lc 'cd /home/admin/rfp-ai-foundation && make up && echo && make ps && echo && make portainer-url && echo && echo "Terminal will remain open for review."; exec bash'
