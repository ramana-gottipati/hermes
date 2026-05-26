#!/usr/bin/env bash
# Deploy Hermes to the VPS. Run from local machine.
#
# Usage: ./scripts/deploy.sh user@vps-host /opt/hermes
set -euo pipefail

REMOTE="${1:?usage: deploy.sh user@host remote_path}"
REMOTE_PATH="${2:-/opt/hermes}"

echo ">> syncing code to ${REMOTE}:${REMOTE_PATH}"
rsync -avz --delete \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.env' \
    --exclude='data' \
    --exclude='logs' \
    ./ "${REMOTE}:${REMOTE_PATH}/"

echo ">> rebuilding + restarting on remote"
ssh "${REMOTE}" "cd ${REMOTE_PATH} && docker compose up -d --build"

echo ">> done. tail logs with:  ssh ${REMOTE} 'cd ${REMOTE_PATH} && docker compose logs -f'"
