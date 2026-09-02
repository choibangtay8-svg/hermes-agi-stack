"""agi-cognition Hermes plugin: exposes the 4 cognitive engines as agent tools.

Engines are loaded DIRECTLY by file path (spec_from_file_location) instead of
`import plugins.*` — host runtimes like Hermes ship their own top-level
`plugins` package, so package-name imports resolve to the wrong tree inside
Hermes. Handlers take ONE positional args dict and return a JSON STRING.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO = None
for _cand in (Path(__file__).resolve().parents[3],           # plugin living inside the repo
              os.environ.get("HERMES_AGI_STACK_HOME"),
              Path.home() / "workspace" / "hermes-agi-stack"):
    if _cand and Path(_cand, "plugins", "causal_sim.py").is_file():
        _REPO = Path(_cand)
        break


def _load(modname: str):
    """Load plugins/<modname>.py directly by file path, cache under a unique name."""
    cache = f"agi_cog_engines.{modname}"
    if cache in sys.modules:
        return sys.modules[cache]
    if _REPO is None:
        raise ImportError("agi-cognition: no hermes-agi-stack repo found")
    path = _REPO / "plugins" / f"{modname}.py"
    spec = importlib.util.spec_from_file_location(cache, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"agi-cognition: cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[cache] = mod
    spec.loader.exec_module(mod)
    return mod


try:
    _causal = _load("causal_sim")
    _curio = _load("curiosity_engine")
    _diale = _load("dialectic_council")
    _shift = _load("paradigm_shift")
    _debater_mod = _load("llm_debater")
    CausalGraph = _causal.CausalGraph
    TraceStep = _causal.TraceStep
    CuriosityEngine = _curio.CuriosityEngine
    DialecticCouncil = _diale.DialecticCouncil
    ParadigmShiftMonitor = _shift.ParadigmShiftMonitor
    make_openai_debater = _debater_mod.make_openai_debater
    _AVAILABLE = True
    _IMPORT_ERROR = None
except Exception as e:  # pragma: no cover
    CausalGraph = CuriosityEngine = DialecticCouncil = None  # type: ignore[assignment]
    make_openai_debater = ParadigmShiftMonitor = None  # type: ignore[assignment]
    _AVAILABLE = False
    _IMPORT_ERROR = str(e)
    logger.warning("agi-cognition: engines not importable: %s", e)

_monitor = None
_council = None


def _monitor_singleton():
    global _monitor
    if _monitor is None:
        _monitor = ParadigmShiftMonitor()
    return _monitor


def _council_singleton():
    global _council
    if _council is None:
        _council = DialecticCouncil(debater=make_openai_debater(), max_rounds=1)
    return _council


def _d(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


# ---------------------------------------------------------------- tools

def _causal_simulate(args, **_):
    if not _AVAILABLE:
        return _d({"error": _IMPORT_ERROR})
    traces = args.get("traces") if isinstance(args, dict) else None
    if not isinstance(traces, list) or not traces:
        return _d({"error": "traces must be a non-empty list of {tool, args, result, ok, duration_ms}"})
    try:
        g = CausalGraph.from_traces(traces)
        prune_at = args.get("prune_threshold")
        pruned = g.prune(float(prune_at)) if prune_at is not None else g.prune()
        return _d({"nodes": len(g.nodes), "edges": len(g.edges),
                   "pruned_spurious": pruned, "graph": g.to_dict()})
    except Exception as exc:  # noqa: BLE001
        return _d({"error": f"causal_simulate failed: {exc}"})


def _curiosity_quests(args, **_):
    if not _AVAILABLE:
        return _d({"error": _IMPORT_ERROR})
    if not isinstance(args, dict):
        return _d({"error": "args must be an object"})
    vault = args.get("vault_path") or str(Path.home() / "knowledge-vault")
    limit = args.get("limit", 5)
    try:
        engine = CuriosityEngine(vault)
        quests = engine.run_idle_cycle()
        return _d({"vault": str(engine.vault_path), "quests": [q.__dict__ for q in quests][:int(limit)],
                   "count": len(quests)})
    except Exception as exc:  # noqa: BLE001
        return _d({"error": f"curiosity_quests failed: {exc}"})


def _dialectic_debate(args, **_):
    if not _AVAILABLE:
        return _d({"error": _IMPORT_ERROR})
    topic = args.get("topic") if isinstance(args, dict) else None
    if not topic or not isinstance(topic, str):
        return _d({"error": "topic must be a non-empty string"})
    try:
        rec = _council_singleton().run_debate(topic)
        return _d({"topic": rec.topic,
                   "turns": [{"role": t.role.value, "claim": t.claim, "confidence": t.confidence} for t in rec.turns],
                   "verdict": rec.verdict, "confidence": rec.confidence,
                   "verified": rec.verified, "notes": rec.notes})
    except Exception as exc:  # noqa: BLE001
        return _d({"error": f"dialectic_debate failed: {exc}"})


def _paradigm_drift_report(args, **_):
    if not _AVAILABLE:
        return _d({"error": _IMPORT_ERROR})
    if not isinstance(args, dict):
        return _d({"error": "args must be an object"})
    skill = args.get("skill")
    ok = args.get("ok")
    monitor = _monitor_singleton()
    if isinstance(skill, str) and isinstance(ok, bool):
        monitor.record(skill, ok)
    events = monitor.detect_drift()
    return _d({"skills_tracked": sorted(monitor.history.keys()),
               "drift_events": [e.__dict__ for e in events],
               "reset_pending": [s for s in set(monitor.history) | set(monitor.events) if monitor.should_reset(s)]})


CAUSAL_SCHEMA = {
    "name": "causal_simulate",
    "description": "Build a causal DAG from tool-execution traces, run counterfactual branch simulation, and prune spurious steps before saving a skill.",
    "parameters": {
        "type": "object",
        "properties": {
            "traces": {"type": "array", "items": {"type": "object"}, "description": "Tool execution traces"},
            "prune_threshold": {"type": "number", "description": "Min counterfactual contribution to keep a node (default 0.05)"},
        },
        "required": ["traces"],
        "additionalProperties": False,
    },
}

CURIOSITY_SCHEMA = {
    "name": "curiosity_quests",
    "description": "Scan the knowledge vault for epistemic gaps (unlinked notes, empty sections, failed runs) and return prioritized learning quests. Use when idle or before planning.",
    "parameters": {
        "type": "object",
        "properties": {
            "vault_path": {"type": "string", "description": "Vault directory (default ~/knowledge-vault)"},
            "limit": {"type": "integer", "description": "Max quests to return (default 5)"},
        },
        "additionalProperties": False,
    },
}

DIALECTIC_SCHEMA = {
    "name": "dialectic_debate",
    "description": "Run a Hegelian thesis/antithesis/synthesis debate on a decision topic, with optional Z3 formal verification and an LLM debater. Use before committing to risky plans.",
    "parameters": {
        "type": "object",
        "properties": {"topic": {"type": "string", "description": "The decision or plan to debate"}},
        "required": ["topic"],
        "additionalProperties": False,
    },
}

DRIFT_SCHEMA = {
    "name": "paradigm_drift_report",
    "description": "Record a skill outcome (ok/fail) and report environmental-drift events plus skills pending an ontology reset. Call after every meaningful skill run.",
    "parameters": {
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "Skill name when recording an outcome"},
            "ok": {"type": "boolean", "description": "True if the skill run succeeded"},
        },
        "additionalProperties": False,
    },
}

_TOOLS = (
    ("causal_simulate", CAUSAL_SCHEMA, _causal_simulate, "\u2699\ufe0f"),
    ("curiosity_quests", CURIOSITY_SCHEMA, _curiosity_quests, "\U0001f50d"),
    ("dialectic_debate", DIALECTIC_SCHEMA, _dialectic_debate, "\u2696\ufe0f"),
    ("paradigm_drift_report", DRIFT_SCHEMA, _paradigm_drift_report, "\U0001f300"),
)


def register(ctx) -> None:
    if not _AVAILABLE:
        logger.warning("agi-cognition: engines unavailable (%s) — tools not registered", _IMPORT_ERROR)
        return
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(name=name, toolset="agi_cognition_toolset",
                          schema=schema, handler=handler, emoji=emoji)
