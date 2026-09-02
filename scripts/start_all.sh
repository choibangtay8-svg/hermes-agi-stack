#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"; mkdir -p .runtime; PIDS=()
cleanup(){ kill "${PIDS[@]}" 2>/dev/null || true; }; trap cleanup EXIT INT TERM
HERMES="${HERMES_CMD:-hermes}"
if [ "${1:-}" = --check ]; then command -v bun >/dev/null && echo 'bun: available' || echo 'bun: missing'; command -v "$HERMES" >/dev/null && echo 'hermes: available' || echo 'hermes: missing'; exit 0; fi
command -v "$HERMES" >/dev/null 2>&1 || { echo "missing Hermes command: $HERMES" >&2; exit 127; }
if [ -f services/gbrain/src/cli.ts ] && command -v bun >/dev/null 2>&1; then bun run services/gbrain/src/cli.ts serve --http --port 8765 >.runtime/gbrain.log 2>&1 & PIDS+=("$!"); fi
read -r -a HARGS <<< "${HERMES_ARGS:-}"
"$HERMES" "${HARGS[@]}" >.runtime/hermes.log 2>&1 & HERMES_PID=$!; PIDS+=("$HERMES_PID")
wait "$HERMES_PID"; status=$?; echo "hermes exited: $status"; exit "$status"
