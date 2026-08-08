#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate Trade

HOST="${APP_HOST:-127.0.0.1}"
PORT="${APP_PORT:-8000}"

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
exec python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
