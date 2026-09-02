#!/usr/bin/env bash
# Idempotent one-shot installer for hermes-agi-stack (Linux/macOS).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
log() { echo "[setup] $*"; }

# ---- 1. bun (>= 1.3.10) — best effort, PATH refreshed in this shell
if ! command -v bun >/dev/null 2>&1 || [ "$(bun --version 2>/dev/null | cut -d. -f1)" -lt 1 ]; then
  log "installing bun..."
  curl -fsSL https://bun.sh/install | bash >/dev/null 2>&1 || log "warning: bun install failed (install manually)"
fi
if [ -x "$HOME/.bun/bin/bun" ]; then export PATH="$HOME/.bun/bin:$PATH"; fi
command -v bun >/dev/null 2>&1 && log "bun: $(bun --version)" || log "warning: bun still missing — gbrain optional"

# ---- 2. Python venv + deps — best effort
if [ ! -x .venv/bin/pip ]; then
  log "creating .venv..."
  rm -rf .venv
  python3 -m venv .venv 2>/dev/null || python3 -m venv --without-pip .venv
  if [ ! -x .venv/bin/pip ]; then
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    .venv/bin/python /tmp/get-pip.py >/dev/null 2>&1 || log "warning: bootstrap pip failed"
  fi
fi
if .venv/bin/pip --version >/dev/null 2>&1; then
  .venv/bin/pip install -q -r requirements.txt || log "warning: pip install failed (offline mode)"
else
  log "warning: no pip in .venv — plugins still importable with system python"
fi

# ---- 3. GBrain checkout — retry when source files are missing (clone-failure marker)
GBRAIN_DIR="services/gbrain"
if [ ! -f "$GBRAIN_DIR/src/cli.ts" ]; then
  rm -rf "$GBRAIN_DIR"
  if command -v git >/dev/null 2>&1 && git clone --depth 1 https://github.com/garrytan/gbrain "$GBRAIN_DIR" 2>/dev/null; then
    log "gbrain cloned"
    if command -v bun >/dev/null 2>&1; then (cd "$GBRAIN_DIR" && bun install --frozen-lockfile) || log "warning: bun install failed"; fi
  else
    mkdir -p "$GBRAIN_DIR"
    [ -f "$GBRAIN_DIR/README.md" ] || cat > "$GBRAIN_DIR/README.md" <<'MD'
# Optional GBrain service
Clone failed during setup. Retry: git clone https://github.com/garrytan/gbrain services/gbrain
MD
    log "warning: gbrain clone failed — offline stub kept"
  fi
else
  log "gbrain: already present"
fi

# ---- 4. Vault init — copy missing entries only, never overwrite
VAULT="${VAULT_PATH:-$HOME/knowledge-vault}"
mkdir -p "$VAULT"
for d in raw_notes entities skills agent_logs; do
  mkdir -p "$VAULT/$d"
  [ -e "$VAULT/$d/.gitkeep" ] || cp "vault_template/$d/.gitkeep" "$VAULT/$d/.gitkeep" 2>/dev/null || touch "$VAULT/$d/.gitkeep"
done
log "vault: $VAULT"

# ---- 5. gbrain local init (PGLite) — only when checkout exists and brain missing
if [ -f "$GBRAIN_DIR/src/cli.ts" ] && command -v bun >/dev/null 2>&1 && [ ! -d "$HOME/.gbrain-brain" ]; then
  (cd "$GBRAIN_DIR" && bun run src/cli.ts init --pglite --non-interactive --no-embedding --path "$HOME/.gbrain-brain" --json) \
    >/dev/null 2>&1 && log "gbrain brain: $HOME/.gbrain-brain" || log "warning: gbrain init failed (run manually: bun run src/cli.ts init)"
fi

# ---- 6. Generated local config (gitignored, machine-specific, never tracked)
mkdir -p config
cat > config/gbrain.config.local.json <<EOF
{
  "vaultPath": "$VAULT",
  "dbPath": "$HOME/.gbrain-brain",
  "mcp": { "transport": "http", "httpPort": 8765, "serveCommand": "bun run src/cli.ts serve --http --port 8765" }
}
EOF
log "config: config/gbrain.config.local.json (gitignored)"

# ---- 7. Final validation
bash -n scripts/*.sh || log "warning: bash syntax issues"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
"$PY" -m py_compile plugins/*.py && log "py_compile OK"
"$PY" -c "import plugins; print('import OK:', sorted(plugins.REGISTRY))" 2>/dev/null || log "warning: plugins import failed"
log "setup complete: vault=$VAULT brain=${HOME}/.gbrain-brain"
