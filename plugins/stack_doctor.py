"""Read-only, fail-open health check for a hermes-agi-stack deployment.

Portable core of the ``stack-doctor`` operator tool: every location is
overridable via environment so cloned deployments work anywhere, not just
the machine this was first written on.

Environment overrides (all optional):
    GBRAIN_URL   GBrain MCP health endpoint (default http://127.0.0.1:8765/health)
    ROUTER_URL   LLM router health endpoint (default http://127.0.0.1:20128/api/health)
    STACK_REPO   repo checkout root (default: parent of this file's package)
    VAULT_PATH   Obsidian vault root (default ~/knowledge-vault)
    BUN_BIN      bun executable (default ~/.bun/bin/bun)

Stdlib only. Every check is independent: one failure degrades to
``unknown`` and never suppresses the remaining lines. Never raises.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

__all__ = ["stack_status", "COMPONENTS"]

COMPONENTS = ("gbrain", "9router", "gateway", "cron", "gbrain checkout",
              "gbrain node_modules", "venv", "vault", "bun")


def _repo_root() -> Path:
    override = os.environ.get("STACK_REPO", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1]


def _http(url: str, key: str, expected) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get(key) == expected:
            version = data.get("version")
            return True, f"ok{f' (v{version})' if version else ''}"
        return False, "unexpected response"
    except Exception:
        return False, "unknown"


def _command(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                timeout=10, check=False)
        return result.returncode == 0, (result.stdout + "\n" + result.stderr).strip()
    except Exception:
        return False, ""


def _line(name: str, ok: bool, detail: str = "") -> str:
    return f"{'✅' if ok else '❌'} {name}: {detail or ('ok' if ok else 'unknown')}"


def stack_status() -> str:
    """Run all checks and return compact Markdown; never raises."""
    try:
        lines = []
        ok, detail = _http(os.environ.get(
            "GBRAIN_URL", "http://127.0.0.1:8765/health"), "status", "ok")
        lines.append(_line("gbrain", ok, detail))
        ok, detail = _http(os.environ.get(
            "ROUTER_URL", "http://127.0.0.1:20128/api/health"), "ok", True)
        lines.append(_line("9router", ok, detail))

        ok, output = _command(["hermes", "gateway", "status"])
        low = output.lower()
        running = ok and ("running" in low or "active" in low)
        lines.append(_line("gateway", running,
                           "running" if running else ("not running" if output else "unknown")))

        ok, output = _command(["hermes", "cron", "list"])
        if ok:
            count = sum(1 for line in output.splitlines()
                        if line.strip() and not line.lower().startswith(("id", "schedule", "no ")))
            lines.append(_line("cron", True, f"{count} active job{'s' if count != 1 else ''}"))
        else:
            lines.append(_line("cron", False))

        repo = _repo_root()
        lines.append(_line("gbrain checkout", (repo / "services/gbrain/src/cli.ts").is_file()))
        lines.append(_line("gbrain node_modules", (repo / "services/gbrain/node_modules").is_dir()))
        venv_python = repo / ".venv/bin/python"
        lines.append(_line("venv", venv_python.is_file() and os.access(venv_python, os.X_OK)))

        vault_override = os.environ.get("VAULT_PATH", "").strip()
        vault = Path(vault_override).expanduser() if vault_override else Path.home() / "knowledge-vault"
        parts = [p for p in ("raw_notes", "entities", "skills", "agent_logs") if (vault / p).is_dir()]
        lines.append(_line("vault", len(parts) == 4,
                           f"{len(parts)}/4 directories" if vault.exists() else "unknown"))

        bun_override = os.environ.get("BUN_BIN", "").strip()
        bun = Path(bun_override).expanduser() if bun_override else Path.home() / ".bun/bin/bun"
        if bun.is_file() and os.access(bun, os.X_OK):
            bok, bout = _command([str(bun), "--version"])
            lines.append(_line("bun", bok, bout.splitlines()[0] if bok and bout else "unknown"))
        else:
            lines.append(_line("bun", False))
        return "\n".join(lines)
    except Exception:
        return "❌ stack-doctor: unknown"
