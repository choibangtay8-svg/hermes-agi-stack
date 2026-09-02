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

Vault layout: `raw_notes/`, `entities/`, `skills/`, `agent_logs/`.

```python
from plugins import REGISTRY
graph = REGISTRY['causal_sim'].from_traces([])
```

## How to Summon Future Agents via this Repo
```bash
git clone https://github.com/<YOUR_USER>/hermes-agi-stack.git && cd hermes-agi-stack && ./scripts/setup.sh
```
Suggested first prompt: “Inspect plugins and improve one contract with tests.”

## Troubleshooting
Offline installs warn and continue; install dependencies later. Missing bun disables GBrain. Port 8765 conflicts require changing deployment command/config.

MIT license. Configuration lives in `config/`; set `VAULT_PATH`, `HERMES_CMD`, and `HERMES_ARGS` as needed.
