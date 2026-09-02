#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
log(){ printf '[setup] %s\n' "$*"; }
need(){ command -v "$1" >/dev/null 2>&1 || { log "warning: missing command $1"; return 1; }; }
need python3 || exit 1
if ! command -v bun >/dev/null 2>&1; then
  if need curl; then curl -fsSL https://bun.sh/install | bash || log 'warning: bun install failed'; else log 'warning: curl unavailable; bun install skipped'; fi
fi
export PATH="$HOME/.bun/bin:$PATH"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -r requirements.txt || log 'warning: pip install failed'
mkdir -p services
if [ ! -f services/gbrain/src/cli.ts ]; then
  if need git; then
    [ -d services/gbrain ] && rm -rf services/gbrain
    git clone https://github.com/garrytan/gbrain services/gbrain || { mkdir -p services/gbrain; printf '# GBrain unavailable\n' > services/gbrain/README.md; log 'warning: gbrain clone failed'; }
  else log 'warning: git unavailable; gbrain clone skipped'; fi
fi
VAULT="${VAULT_PATH:-$HOME/knowledge-vault}"; mkdir -p "$VAULT"
for d in raw_notes entities skills agent_logs; do mkdir -p "$VAULT/$d"; [ -e "$VAULT/$d/.gitkeep" ] || cp "vault_template/$d/.gitkeep" "$VAULT/$d/.gitkeep"; done
python3 - "$VAULT" <<'PY'
import json,sys
from pathlib import Path
p=Path('config/gbrain.config.local.json'); v=Path(sys.argv[1]).resolve(); p.write_text(json.dumps({'vaultPath':str(v),'dbPath':str(v/'.gbrain.pglite'),'mcp':{'httpPort':8765}},indent=2)+'\n')
PY
bash -n scripts/*.sh; .venv/bin/python -m py_compile plugins/*.py
log "complete vault=$VAULT"
