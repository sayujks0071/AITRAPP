#!/bin/bash
# 7-minute Binance validation flight
set -Eeuo pipefail

API="http://localhost:8000"
TIMEOUT=420  # 7 minutes

echo "🚀 Binance Validation Flight (7 min)"
echo "===================================="
echo ""

# 0) Keys + deps check
echo "0️⃣  Checking keys and deps..."
if [ -z "${BINANCE_API_KEY:-}" ] || [ -z "${BINANCE_API_SECRET:-}" ]; then
    echo "❌ BINANCE_API_KEY and BINANCE_API_SECRET must be set"
    exit 1
fi
echo "✅ Keys present"

# Check docker services
if ! docker compose ps postgres redis 2>/dev/null | grep -q "Up"; then
    echo "⚠️  Starting postgres/redis..."
    docker compose up -d postgres redis
    sleep 5
fi
echo "✅ Infra ready"
echo ""

# 1) Paper config
echo "1️⃣  Setting up paper config (BINANCE_SPOT)..."
cp configs/crypto_paper.yaml configs/app.yaml
echo "✅ Config ready"
echo ""

# 2) Preflight + launch
echo "2️⃣  Running GO/NO-GO check..."
if ! make crypto-gonogo; then
    echo "❌ GO/NO-GO check failed"
    exit 1
fi
echo "✅ GO/NO-GO PASS"
echo ""

echo "3️⃣  Launching API (background)..."
make crypto-canary-launch &
LAUNCH_PID=$!

# Wait for /ready
echo "   Waiting for /ready..."
for i in {1..30}; do
    if curl -fsS "$API/ready" >/dev/null 2>&1; then
        echo "✅ API ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API not ready after 60s"
        kill $LAUNCH_PID 2>/dev/null || true
        exit 1
    fi
    sleep 2
done
echo ""

# 4) Watch metrics (quick snapshot)
echo "4️⃣  Snapshot metrics (first 30s)..."
sleep 30
echo ""
echo "   Key metrics:"
curl -s "$API/metrics" 2>/dev/null | grep -E "^trader_(is_leader|.*heartbeat_seconds|oco_orphans_total|binance_used_weight_1m|binance_order_count_1m|binance_listenkey_renew_total)" | head -10 || echo "   ⚠️  Metrics not available yet"
echo ""

# 5) OCO drill
echo "5️⃣  Running OCO drill (native Binance OCO)..."
if ! make crypto-oco-drill; then
    echo "❌ OCO drill failed"
    kill $LAUNCH_PID 2>/dev/null || true
    exit 1
fi
echo "✅ OCO drill PASS"
echo ""

# 6) Final metrics check
echo "6️⃣  Final metrics check..."
sleep 10
echo ""
echo "   Health snapshot:"
curl -s "$API/health" | jq '{mode, crypto_venue, allowed_symbols, status}' || echo "   ⚠️  Health check failed"
echo ""
echo "   Critical metrics:"
curl -s "$API/metrics" 2>/dev/null | grep -E "^trader_(is_leader|oco_orphans_total|binance_used_weight_1m)" || echo "   ⚠️  Metrics not available"
echo ""

# 7) Scorer + report
echo "7️⃣  Running Day-1 scorer..."
if ! make score-crypto-day1; then
    echo "❌ Scorer failed"
    kill $LAUNCH_PID 2>/dev/null || true
    exit 1
fi
echo "✅ Scorer PASS"
echo ""

echo "8️⃣  Generating report..."
make crypto-report || echo "⚠️  Report generation failed (may be OK if no history)"
echo ""

# Final validation
echo "📊 Validation Summary"
echo "===================="
SCORER_JSON=$(ls -t reports/burnin/crypto_day1_*.json 2>/dev/null | head -1)
if [ -n "$SCORER_JSON" ]; then
    STATUS=$(jq -r '.status // "UNKNOWN"' "$SCORER_JSON" 2>/dev/null || echo "UNKNOWN")
    if [ "$STATUS" = "PASS" ]; then
        echo "✅ Scorer: PASS"
    else
        echo "❌ Scorer: $STATUS"
        cat "$SCORER_JSON" | jq '.' || true
    fi
else
    echo "⚠️  No scorer JSON found"
fi

echo ""
echo "🎯 Validation flight complete!"
echo ""
echo "Next steps:"
echo "  - Review metrics: make watch-crypto"
echo "  - Check report: make crypto-report"
echo "  - When ready: cp configs/crypto_canary_live.yaml configs/app.yaml && make crypto-canary-launch"


