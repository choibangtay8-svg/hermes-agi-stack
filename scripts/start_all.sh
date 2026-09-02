#!/usr/bin/env bash
# Boot the live stack: GBrain MCP (:8765) + Hermes Agent. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
mkdir -p .runtime
PIDS=()
cleanup() { kill "${PIDS[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Resolve bun (fresh shells lack it even after installer ran)
if ! command -v bun >/dev/null 2>&1 && [ -x "$HOME/.bun/bin/bun" ]; then
  export PATH="$HOME/.bun/bin:$PATH"
fi

if [ "${1:-}" = --check ]; then
  echo "gbrain checkout: $([ -f services/gbrain/package.json ] && echo yes || echo no)"
  echo "bun: $(command -v bun >/dev/null 2>&1 && echo available || echo MISSING)"
  echo "hermes: $(command -v "${HERMES_CMD:-hermes}" >/dev/null 2>&1 && echo available || echo MISSING)"
  echo "mcp token env: $([ -n "${GBRAIN_MCP_TOKEN:-}" ] && echo set || echo not-set)"
  exit 0
fi

# 1) GBrain MCP (best-effort: a missing/broken GBrain never blocks Hermes)
GBRAIN_PID=""
if [ -f services/gbrain/src/cli.ts ] && command -v bun >/dev/null 2>&1; then
  bun run services/gbrain/src/cli.ts serve --http --port 8765 >.runtime/gbrain.log 2>&1 &
  GBRAIN_PID=$!; PIDS+=("$GBRAIN_PID")
  echo "[start_all] gbrain MCP pid=$GBRAIN_PID (log: .runtime/gbrain.log)"
  sleep 3
  if ! kill -0 "$GBRAIN_PID" 2>/dev/null; then
    echo "[start_all] WARNING: gbrain exited early — see .runtime/gbrain.log (Hermes continues without it)"
    GBRAIN_PID=""
  else
    curl -sf -m 5 http://127.0.0.1:8765/health >/dev/null 2>&1 \
      && echo "[start_all] gbrain MCP healthy on :8765" \
      || echo "[start_all] WARNING: gbrain health check failed (may still be starting)"
  fi
else
  echo "[start_all] gbrain not installed — continuing without memory layer"
fi

# 2) Hermes (required)
HERMES="${HERMES_CMD:-hermes}"
command -v "$HERMES" >/dev/null 2>&1 || { echo "[start_all] missing Hermes command: $HERMES" >&2; exit 127; }
read -r -a HARGS <<< "${HERMES_ARGS:-}"
"$HERMES" "${HARGS[@]}" >.runtime/hermes.log 2>&1 &
HERMES_PID=$!; PIDS+=("$HERMES_PID")
echo "[start_all] hermes pid=$HERMES_PID (log: .runtime/hermes.log)"

# 3) Supervise Hermes; report gbrain death without killing Hermes
wait "$HERMES_PID"; status=$?
echo "[start_all] hermes exited: $status"
exit "$status"
