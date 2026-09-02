"""LLM debater adapters for DialecticCouncil (OpenAI-compatible, stdlib-only).

Deliberately standalone: no imports from the `plugins` package (avoids name
collisions under host runtimes that ship their own `plugins` package).
Roles are duck-typed — any object with a `.value` (e.g. Role enum) or a plain
string ("thesis"/"antithesis"/"synthesis") works.

`make_openai_debater()` returns a DebaterFn callable that drives a real LLM
through an OpenAI-compatible /chat/completions endpoint (default: local Hermes
9Router gateway). Falls back to the deterministic heuristic when the endpoint
is unreachable, so councils never hard-fail offline.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error  # noqa: F401  (re-exported for callers that probe)
import urllib.request
from typing import Any, Callable

log = logging.getLogger(__name__)

ROLE_SYSTEM = {
    "thesis": (
        "You are the THESIS in a Hegelian debate. State the strongest positive case "
        "for the topic in <=3 sentences. Be concrete, name assumptions."
    ),
    "antithesis": (
        "You are the ANTITHESIS in a Hegelian debate. Attack the thesis: strongest "
        "concrete objection, failure modes, stressors. <=3 sentences. No pleasantries."
    ),
    "synthesis": (
        "You are the SYNTHESIS in a Hegelian debate. Merge the strongest parts of "
        "thesis and antithesis into a conditional position plus falsifiable checks. "
        "<=3 sentences. Include at least one measurable test."
    ),
}

DEFAULT_BASE_URL = os.environ.get("HERMES_GATEWAY_URL", "http://127.0.0.1:20128/v1")
DEFAULT_MODEL = os.environ.get("HERMES_GATEWAY_MODEL", "ptw/gpt-5.6-sol")


def _role_key(role: Any) -> str:
    v = getattr(role, "value", role)
    s = str(v).lower()
    for k in ROLE_SYSTEM:
        if k in s:
            return k
    return "thesis"


def _chat(base_url: str, model: str, system: str, user: str, api_key: str,
          timeout: float = 30.0) -> str:
    """One OpenAI-compatible chat completion. Raises on any failure."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": 300,
        "temperature": 0.4,
        # NOTE: this gateway returns EMPTY content for stream:false on some
        # models; streaming works reliably, so we stream and parse SSE below.
    }).encode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {api_key}"} if api_key else {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
    try:
        body = json.loads(raw)
        content = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError):
        # Some gateways stream SSE even with stream:false — collect deltas.
        parts = []
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk in ("", "[DONE]"):
                continue
            try:
                delta = json.loads(chunk)["choices"][0].get("delta", {})
            except (ValueError, KeyError, IndexError):
                continue
            piece = delta.get("content")
            if isinstance(piece, str):
                parts.append(piece)
        content = "".join(parts)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("empty completion")
    return content.strip()


def _history_digest(turns: list) -> str:
    out = []
    for t in turns:
        out.append(f"[{_role_key(t.role if hasattr(t, 'role') else t)}] "
                   f"{getattr(t, 'claim', t)} ({getattr(t, 'critique', '')})")
    return "\n".join(out) or "(no prior turns)"


def make_openai_debater(base_url: str | None = None, model: str | None = None,
                        api_key: str | None = None,
                        fallback: Callable[..., str] | None = None) -> Callable[..., Any]:
    """Build a DebaterFn(role, topic, turns) backed by an LLM endpoint.

    On network/API failure, logs and falls back to the deterministic heuristic so
    run_debate() always produces a record.
    """
    base_url = base_url or DEFAULT_BASE_URL
    model = model or DEFAULT_MODEL
    api_key = api_key or os.environ.get("HERMES_GATEWAY_API_KEY", "")
    fallback = fallback or _heuristic_fallback

    def debater(role, topic, turns, **_):
        key = _role_key(role)
        try:
            return _chat(base_url, model, ROLE_SYSTEM[key],
                         f"TOPIC: {topic}\n\nDEBATE SO FAR:\n{_history_digest(turns)}\n\nYour turn:",
                         api_key)
        except Exception as exc:  # noqa: BLE001 - never fail the council
            log.warning("llm_debater: %s %s failed (%s); falling back", model, key, exc)
            return fallback(role, topic, turns)

    debater.model = model  # type: ignore[attr-defined]
    debater.base_url = base_url  # type: ignore[attr-defined]
    return debater


def _heuristic_fallback(role, topic, turns, **_):
    key = _role_key(role)
    if key == "thesis":
        return f"{topic} is viable under stated constraints."
    if key == "antithesis":
        return f"Objection: {topic} may fail under scale, cost, or adversarial stress."
    return f"Synthesis: adopt {topic} conditionally; verify assumptions with measurable tests."


__all__ = ["make_openai_debater", "DEFAULT_BASE_URL", "DEFAULT_MODEL"]
