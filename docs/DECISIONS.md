# Decisions

- GBrain remains an optional checkout; Python plugins run offline with lazy imports.
- `~/knowledge-vault` is initialized only for missing files; existing notes are never overwritten.
- Configuration uses JSON/YAML paths and localhost HTTP port 8765 by default.
- Hermes command is configurable via `HERMES_CMD`; default is `hermes`.
- No credentials or generated databases belong in git.
- GBrain CLI may vary; start script uses best-effort `bun run ... mcp --port 8765`.
- Missing networkx/z3/GBrain uses pure-Python or deterministic offline fallbacks.
- Setup preserves unknown JSON config keys and never overwrites vault files.
- This environment lacked usable `ensurepip`, so `.venv` validation could not run; system Python unittest/compile checks passed.

## REVIEW NOTES

- Added dataclass field defaults to prevent shared mutable state.
- Counterfactual overrides now use isolated scenario data and report positive removal contribution (`before - after`).
- Pruning uses contribution directly and does not mutate graph during evaluation.
- Curiosity quest source lists are copied and deduplicated.
- Drift detection reports rising failure rate with failure-rate fields and handles uneven windows.
- Setup checks required commands, quotes paths, and keeps optional Bun/GBrain failures as warnings.
- Hermes config marks stdio transport active and HTTP transport inactive.

## PASS 4 FIXES

- Review A MED: causal traces tolerate null args/invalid duration; counterfactual graph attrs stay synchronized; curiosity uses exact wikilinks and checks each heading body; paradigm drift emits success rates, equal halves, and deduplicated crossing events.
- Review A LOW: repeated drift polling no longer duplicates events.
- Review B HIGH: start_all uses GBrain `serve` CLI, waits Hermes, propagates status, and fails missing Hermes.
- Review B MED: quoted Hermes args, clone retry on missing source, generated local config.
- Review B LOW: nested HTTP port/CLI args fixed; Bun PATH refreshed.
- CI dependency installation now fails honestly.

## LIVE RUNTIME (2026-09-03, Step 2)

- Plugin `agi-cognition` installed at ~/.hermes/plugins/ and enabled; `tools.toolsets`
  must contain `agi_cognition_toolset` for tools to surface (verified general tools stay
  visible when the key is present, so it is additive, not a whitelist in practice).
- Engines load via spec_from_file_location (hermes ships its own `plugins` package;
  package-name imports resolve to the wrong tree under Hermes runtime).
- 9Router gateway returns EMPTY content for stream:false on gpt-5.6-sol; llm_debater
  streams by default and parses SSE deltas (fallback: heuristic, never fatal).
- Debate confidence values are pass-2 hardcoded priors (.72/.68/.76), not LLM self-rates —
  polish candidate.
- GBrain live: cloned v0.48.2, bun 1.4.0, PGLite brain at ~/.gbrain-brain (v145, 140
  migrations, search_mode conservative auto-picked: no expansion API key). MCP HTTP :8765
  verified: /health ok, initialize handshake ok, tools/list returns 119 tools. Auth:
  MCP tokens via `gbrain auth create <name>` (NOT the /admin bootstrap token). Serve holds
  the PGLite lock; other CLI writes must stop serve first.
- KNOWN ISSUE: embedding width mismatch warning at serve boot (schema vector(1024) vs
  gateway default 1280). Writes that embed will fail until fixed with
  `gbrain reinit-pglite --embedding-model zeroentropyai:zembed-1 --embedding-dimensions 1280`
  (destructive) or pinning GBRAIN_EMBEDDING_DIMENSIONS=1024 in env. Deferred: no real
  embeddings written yet, so no data loss either way.
- start_all.sh rewritten: bun PATH refresh, gbrain best-effort (health-checked, never
  blocks Hermes), Hermes required (exit 127 if missing), HERMES_ARGS word-safe, real
  exit-status propagation. setup.sh rewritten: idempotent, clone-retry on missing source,
  generated local config gitignored (config/gbrain.config.local.json).

## DAEMON

- Processed quests use truncated SHA-1 keys in `agent_logs/.curiosity_state.json`. This avoids mutating note frontmatter and keeps source notes fully user-owned; old scars are never re-mined.
- Artifact write happens before Hermes research. A failed or timed-out LLM call therefore leaves every discovered quest recoverable with `research pending` status.
- GBrain sync is best effort. Network, authentication, protocol, and tool failures only warn; local Markdown remains authoritative and cycle processing still completes.

## DISCORD BRIEFINGS (2026-09-03, Step 2b)

- scripts/discord_notify.py: stdlib webhook client, reads DISCORD_WEBHOOK_URL from
  repo .env (gitignored, 0600) or env var. Discord 403s the default urllib UA — must
  send User-Agent header. Blurple 0x5865F2, embed fields per user spec.
- Wired into curiosity_tick.py AFTER research (quest-processed path only); smart-sleep
  path exits 0 before any notification — verified silent tick sends nothing.
- Test: live 204 from real webhook; silent tick produced no webhook call.

## STACK-DOCTOR (2026-09-03, Step 3)
- New `plugins/stack_doctor.py`: read-only 9-check deployment health probe
  (gbrain/9router/gateway/cron/checkout/node_modules/venv/vault/bun).
- All locations env-overridable (STACK_REPO/VAULT_PATH/BUN_BIN/GBRAIN_URL/
  ROUTER_URL) so cloned deployments work anywhere; repo default for
  STACK_REPO is the checkout itself. Local ~/.hermes adapter kept as the
  deployed wrapper (works, untouched); repo module is the portable source.
- tests/test_stack_doctor.py: component coverage, offline degradation,
  env-override honored (stdlib unittest only).
