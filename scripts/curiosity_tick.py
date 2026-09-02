"""Run one curiosity daemon cycle."""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys

from plugins.curiosity_engine import CuriosityEngine, GBrainSync

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from scripts.discord_notify import notify as discord_notify  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--vault', default=os.environ.get('VAULT_PATH', '~/knowledge-vault'))
    args = parser.parse_args(argv)
    try:
        engine = CuriosityEngine(args.vault)
        quests = engine.propose_quests()
        if not quests:
            return 0
        artifact = engine.write_artifact(quests)
        if not artifact.is_file():
            raise RuntimeError('artifact write failed')
        prompt = 'Research every curiosity quest below in one response. Cite useful sources when possible.\n\n' + '\n'.join(
            f'- {quest.topic}: {quest.reason} (priority {quest.priority})' for quest in quests
        )
        try:
            command = shlex.split(os.environ.get('HERMES_CMD', 'hermes')) + ['chat', '-q', prompt]
            run = subprocess.run(command, text=True, capture_output=True, timeout=240)
            if run.returncode:
                raise RuntimeError(run.stderr.strip() or f'Hermes exited {run.returncode}')
            addition = '\n## Research\n\nstatus: researched\n\n' + run.stdout.strip() + '\n'
        except Exception as exc:
            addition = f'\n## Research\n\nstatus: open\n\nresearch pending: {exc}\n'
        artifact.write_text(artifact.read_text() + addition)
        for quest in quests:
            engine.mark_processed(quest.topic)
        body = artifact.read_text()
        synced = GBrainSync().sync_page(artifact.stem, body)
        notified = discord_notify(artifact, [q.topic for q in quests], body,
                                  env_file=__import__('pathlib').Path(__file__).resolve().parents[1] / '.env')
        print(f'curiosity: processed {len(quests)} quest(s); artifact={artifact}; '
              f'gbrain={"synced" if synced else "pending"}; discord={"sent" if notified else "not-sent"}')
        return 3
    except Exception as exc:
        print(f'curiosity: error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
