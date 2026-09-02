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
