#!/usr/bin/env bash
# Starts the backend fully detached for local smoke testing.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend"
LOG="${LOG:-/tmp/opencode/clinicdesk-api.log}"

cd "$BACKEND_DIR"
setsid .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 \
  >"$LOG" 2>&1 </dev/null &
disown || true

for _ in $(seq 1 30); do
  if curl -sf -m 1 http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "backend up, logging to $LOG"
    exit 0
  fi
  sleep 0.5
done

echo "backend failed to start; last log lines:" >&2
tail -20 "$LOG" >&2
exit 1