#!/usr/bin/env bash
# Starts the Vite dev server fully detached for local smoke testing.
set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/frontend"
LOG="${LOG:-/tmp/opencode/clinicdesk-web.log}"

cd "$FRONTEND_DIR"
setsid npm run dev -- --host 127.0.0.1 --port 5173 >"$LOG" 2>&1 </dev/null &
disown || true

for _ in $(seq 1 40); do
  if curl -sf -m 1 http://127.0.0.1:5173/ >/dev/null 2>&1; then
    echo "frontend up on http://127.0.0.1:5173, logging to $LOG"
    exit 0
  fi
  sleep 0.5
done

echo "frontend failed to start; last log lines:" >&2
tail -20 "$LOG" >&2
exit 1