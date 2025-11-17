#!/bin/bash
# 30-second pre-launch smoke test

set -euo pipefail

echo "🔍 30-Second Pre-Launch Smoke Test"
echo "=================================="
echo ""

# 1. Keys
echo "1️⃣  Checking API keys..."
if [ -n "${BINANCE_TESTNET:-}" ] && [ "${BINANCE_TESTNET}" = "1" ]; then
    echo "   ℹ️  Using Binance Testnet"
    echo "${BINANCE_API_KEY:?}" >/dev/null && echo "${BINANCE_API_SECRET:?}" >/dev/null
else
    echo "${BINANCE_API_KEY:?}" >/dev/null && echo "${BINANCE_API_SECRET:?}" >/dev/null
fi
echo "   ✅ API keys set"
echo ""

# 2. Clock drift
echo "2️⃣  Checking clock drift..."
DRIFT=$(python3 - <<'PY'
import time
import datetime as dt
drift = abs(time.time() - dt.datetime.utcnow().timestamp())
print(f"{drift:.2f}")
PY
)

# Check if drift is acceptable (< 2s)
if command -v bc >/dev/null 2>&1; then
    if (( $(echo "$DRIFT < 2.0" | bc -l) )); then
        echo "   ✅ Clock drift: ${DRIFT}s (< 2s)"
    else
        echo "   ⚠️  Clock drift: ${DRIFT}s (>= 2s, check NTP)"
    fi
else
    # Fallback if bc not available
    if awk "BEGIN {exit !($DRIFT < 2.0)}"; then
        echo "   ✅ Clock drift: ${DRIFT}s (< 2s)"
    else
        echo "   ⚠️  Clock drift: ${DRIFT}s (>= 2s, check NTP)"
    fi
fi
echo ""

# 3. UTC time
echo "3️⃣  UTC time:"
date -u
echo ""

# 4. Health check (if API running)
echo "4️⃣  Router & venue sanity..."
if curl -fsS http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH=$(curl -fsS http://localhost:8000/health)
    echo "$HEALTH" | jq '{mode,crypto_venue,allowed_symbols,precision:.crypto_precision,fees:.crypto_fees}' 2>/dev/null || echo "$HEALTH"
    echo "   ✅ Health check passed"
else
    echo "   ℹ️  API not running (will start during launch)"
fi
echo ""

# 5. GO/NO-GO
echo "5️⃣  Running GO/NO-GO check..."
if bash scripts/crypto_gonogo_check.sh; then
    echo ""
    echo "✅ All checks PASSED - Ready to launch!"
    exit 0
else
    echo ""
    echo "❌ GO/NO-GO check FAILED - Fix issues before launching"
    exit 1
fi

