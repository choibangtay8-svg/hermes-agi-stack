#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDFILE="$ROOT/.runtime/curiosity_daemon.pid"
LOGFILE="$ROOT/.runtime/curiosity_daemon.log"
alive() { [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }
case "${1:-}" in
  start)
    if alive; then echo "curiosity daemon already running (pid $(cat "$PIDFILE"))"; exit 1; fi
    mkdir -p "$ROOT/.runtime"; rm -f "$PIDFILE"
    nohup setsid bash -c 'while true; do bash "$1/scripts/cron_tick.sh" >>"$2" 2>&1 || [[ $? -eq 3 ]]; sleep "${CURIOSITY_INTERVAL:-3600}"; done' _ "$ROOT" "$LOGFILE" >/dev/null 2>&1 &
    echo "$!" > "$PIDFILE"; echo "curiosity daemon started (pid $!)"
    ;;
  stop)
    if ! alive; then rm -f "$PIDFILE"; echo "curiosity daemon not running"; exit 1; fi
    pid="$(cat "$PIDFILE")"; kill -- "-$pid" 2>/dev/null || kill "$pid"; rm -f "$PIDFILE"; echo "curiosity daemon stopped"
    ;;
  status)
    if alive; then echo "curiosity daemon alive (pid $(cat "$PIDFILE"))"; else echo "curiosity daemon dead"; fi
    [[ -f "$LOGFILE" ]] && tail -5 "$LOGFILE"
    ;;
  tick) exec bash "$ROOT/scripts/cron_tick.sh" ;;
  *) echo "Usage: $0 {start|stop|status|tick}" >&2; exit 1 ;;
esac
