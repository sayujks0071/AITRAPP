#!/usr/bin/env bash
# External watchdog ping helper.
# Usage:
#   WATCHDOG_URL="https://hc-ping.com/your-id" ./scripts/heartbeat_ping.sh
#   (place in crontab on a different host for true out-of-process monitoring)

set -euo pipefail

SIDECAR_HOST=${SIDECAR_HOST:-localhost}
SIDECAR_PORT=${SIDECAR_PORT:-8080}
SIDECAR_HEALTH_URL=${SIDECAR_HEALTH_URL:-http://${SIDECAR_HOST}:${SIDECAR_PORT}/health}

echo "🔍 Checking sidecar health at ${SIDECAR_HEALTH_URL}..."
if ! curl -fsS -m 5 "${SIDECAR_HEALTH_URL}" >/dev/null; then
  echo "❌ Sidecar health check failed (logic heartbeat stale or sidecar down)" >&2
  exit 2
fi

if [ -z "${WATCHDOG_URL:-}" ]; then
  echo "WATCHDOG_URL not set; skipping external watchdog ping." >&2
  exit 0
fi

timestamp="$(date -Iseconds)"
curl -fsS -m 5 -X POST -H "Content-Type: text/plain" \
  --data "aitrapp heartbeat ${timestamp}" \
  "${WATCHDOG_URL}" >/dev/null
echo "✅ Watchdog ping sent at ${timestamp}"
