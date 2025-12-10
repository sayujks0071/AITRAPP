#!/usr/bin/env bash
# Periodically run the WebSocket monitor and emit status lines.
# Usage: scripts/ws_monitor_loop.sh [interval_seconds] [threshold_seconds]

set -euo pipefail

INTERVAL="${1:-120}"
THRESHOLD="${2:-300}"

echo "Starting ws monitor loop: interval=${INTERVAL}s, threshold=${THRESHOLD}s"

while true; do
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  status="$(python3 scripts/ws_monitor.py "${THRESHOLD}" 2>&1 || true)"
  echo "[${ts}] ${status}"
  sleep "${INTERVAL}"
done
