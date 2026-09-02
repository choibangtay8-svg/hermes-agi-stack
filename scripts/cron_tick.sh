#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
PYTHON=python3
[[ -x "$ROOT/.venv/bin/python" ]] && PYTHON="$ROOT/.venv/bin/python"
if PYTHONNOUSERSITE=1 "$PYTHON" -m scripts.curiosity_tick --quiet; then
  exit 0
else
  status=$?
fi
[[ $status -eq 3 ]] && exit 3
log "curiosity tick failed (exit $status)"
exit 1
