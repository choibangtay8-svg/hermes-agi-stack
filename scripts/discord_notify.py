"""Discord webhook notifier for the curiosity daemon (stdlib only, silent on sleep).

Reads DISCORD_WEBHOOK_URL from the repo's gitignored `.env` (KEY=VALUE lines) or the
process env. Posts a professional embed. Every failure path returns False and logs —
the caller only invokes this AFTER a quest was processed, so smart sleep never pings.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

EMBED_COLOR = 0x5865F2  # Discord blurple


def load_webhook(env_file: str | Path | None = None) -> str:
    """Resolve DISCORD_WEBHOOK_URL: process env first, then the repo .env."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if url:
        return url
    candidates = [Path(env_file)] if env_file else [
        Path(__file__).resolve().parents[1] / ".env",   # repo root when run from scripts/
        Path.cwd() / ".env",
    ]
    for path in candidates:
        try:
            if not path.is_file():
                continue
            for line in path.read_text().splitlines():
                line = line.strip()
                if line.startswith("DISCORD_WEBHOOK_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:  # noqa: BLE001 - unreadable .env is not fatal
            continue
    return ""


def _insights_from_research(md_body: str, fallback: list[str], limit: int = 3) -> list[str]:
    """Pull the 3 most useful bullets from the artifact's Research section."""
    insights: list[str] = []
    in_research = False
    for line in md_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_research = stripped.lower().startswith("## research")
            continue
        if not in_research:
            continue
        if stripped[:2] in ("- ", "* ") or stripped.startswith("• "):
            item = stripped.lstrip("-*• ").strip()
            if item:
                insights.append(item[:250])
        elif not insights and len(stripped) > 25 and not stripped.startswith(("Warning:", "Query:", "Resume", "Session:", "Title:", "Duration:", "Messages:")):
            insights.append(stripped[:250])
    if not insights:
        insights = [f"New epistemic gap: {t}" for t in fallback]
    return insights[:limit]


def build_embed(artifact_path: str | Path, topics: list[str], md_body: str = "",
                vault_label: str = "knowledge-vault") -> dict:
    """Build a Discord embed dict per the briefing spec."""
    artifact = Path(artifact_path)
    title_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    insight_lines = "\n".join(f"• {s}" for s in _insights_from_research(md_body, topics))
    return {
        "embeds": [{
            "title": f"🧠 Hermes Curiosity Briefing — {title_ts}",
            "color": EMBED_COLOR,
            "fields": [
                {"name": "📌 Topic / Orphan Note",
                 "value": "\n".join(topics)[:1024] or "(none)",
                 "inline": False},
                {"name": "💡 Key Insights",
                 "value": insight_lines[:1024] or "(research pending)",
                 "inline": False},
                {"name": "📂 Vault Artifact",
                 "value": f"`{vault_label}/{artifact.parent.name}/{artifact.name}`",
                 "inline": False},
            ],
            "footer": {"text": "curiosity-daemon · hermes-agi-stack"},
        }],
    }


def send(webhook_url: str, payload: dict, timeout: float = 10.0) -> bool:
    """POST the payload. Returns True on 2xx. Never raises; never logs the URL."""
    if not webhook_url:
        log.warning("discord_notify: no webhook configured")
        return False
    try:
        req = urllib.request.Request(
            webhook_url, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": "HermesCuriosityDaemon/1.0"},  # Discord 403s default UA
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001 - notification must never break the daemon
        log.warning("discord_notify: send failed: %s", exc)
        return False


def notify(artifact_path: str | Path, topics: list[str], md_body: str = "",
           env_file: str | Path | None = None) -> bool:
    """One-shot briefing. Silent when no webhook is configured (returns False)."""
    url = load_webhook(env_file)
    if not url:
        return False
    return send(url, build_embed(artifact_path, topics, md_body))


__all__ = ["load_webhook", "build_embed", "send", "notify", "EMBED_COLOR"]
