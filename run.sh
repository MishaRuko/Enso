#!/usr/bin/env bash
# Run backend and frontend simultaneously.
# Ctrl-C kills both.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Kill any stale processes on the ports
lsof -ti:8100,3000 | xargs kill -9 2>/dev/null || true

echo "Starting backend  → http://localhost:8100"
echo "Starting frontend → http://localhost:3000"
echo ""

# Kill both children when this script exits (Ctrl-C or error)
trap 'echo ""; echo "Stopping..."; kill $(jobs -p) 2>/dev/null; exit' INT TERM EXIT

(
  cd "$ROOT/backend"
  uv run --project "$ROOT" uvicorn src.main:app --reload --host 0.0.0.0 --port 8100
) &

(
  cd "$ROOT/frontend/designer-next"
  pnpm dev
) &

# Wait for either process to exit
wait -n 2>/dev/null || wait
