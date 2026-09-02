# hermes-agi-stack

Obsidian vault, optional GBrain memory, Hermes Agent, and four offline-safe cognitive middleware plugins.

## Setup

```bash
bash scripts/setup.sh
bash scripts/start_all.sh
```

GBrain checkout and Python dependencies are optional at development time. `HERMES_CMD` overrides Hermes executable.

## Architecture
```text
Obsidian <-> GBrain (PGLite/MCP) <-> Hermes Agent <-> 4 Cognitive Plugins
```

| Component | Purpose |
|---|---|
| causal_sim | Trace DAG and counterfactuals |
| dialectic_council | Deterministic thesis/antithesis/synthesis |
| curiosity_engine | Vault gaps and learning quests |
| paradigm_shift | Failure drift and reset events |
| stack_doctor | Read-only deployment health check (env-overridable paths) |

Vault layout: `raw_notes/`, `entities/`, `skills/`, `agent_logs/`.

```python
from plugins import REGISTRY
graph = REGISTRY['causal_sim'].from_traces([])
```

## Curiosity Daemon (24/7)

Daemon scans vault for knowledge gaps. Empty scans sleep without network or LLM use. Nonempty scans create one durable artifact, ask Hermes to research all new quests in one call, record processed topics, then attempt GBrain sync.

| Guardrail | Behavior |
|---|---|
| Smart sleep | No quests means no LLM and no network |
| Anti-loop | SHA-1 topic scars prevent repeated mining |
| Artifacts | Markdown saved before research starts |
| GBrain sync | Best effort; local artifact remains authoritative |

```bash
scripts/run_daemon.sh start
scripts/run_daemon.sh status
scripts/run_daemon.sh stop

# One synchronous cycle
scripts/cron_tick.sh
```

Hourly crontab alternative:

```cron
0 * * * * /root/workspace/hermes-agi-stack/scripts/cron_tick.sh
```

Artifacts land in `~/knowledge-vault/agent_logs/curiosity_<timestamp>.md`. Processed-topic state lives at `~/knowledge-vault/agent_logs/.curiosity_state.json`. Set `VAULT_PATH` or pass `--vault` to `python -m scripts.curiosity_tick` for another vault.

## How to Summon Future Agents via this Repo
```bash
git clone https://github.com/<YOUR_USER>/hermes-agi-stack.git && cd hermes-agi-stack && ./scripts/setup.sh
```
Suggested first prompt: “Inspect plugins and improve one contract with tests.”

## Troubleshooting
Offline installs warn and continue; install dependencies later. Missing bun disables GBrain. Port 8765 conflicts require changing deployment command/config.

MIT license. Configuration lives in `config/`; set `VAULT_PATH`, `HERMES_CMD`, and `HERMES_ARGS` as needed.
