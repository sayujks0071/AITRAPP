#!/bin/bash
# Quick GO/NO-GO check before canary launch

API="${API:-http://localhost:8000}"

echo "🔍 GO/NO-GO Check"
echo "================="
echo ""

# 1. Ready endpoint
echo "1️⃣  Checking /ready..."
READY=$(curl -s -o /dev/null -w "%{http_code}" "$API/ready" 2>/dev/null || echo "000")
if [ "$READY" = "200" ]; then
    echo "   ✅ /ready returns 200"
else
    echo "   ❌ /ready returns $READY"
    exit 1
fi
echo ""

# 2. Leader lock
echo "2️⃣  Checking leader lock..."
LEADER=$(curl -s "$API/metrics" 2>/dev/null | grep '^trader_is_leader' | awk '{print $2}' || echo "0")
if [ "$LEADER" = "1" ]; then
    echo "   ✅ trader_is_leader = 1"
else
    echo "   ❌ trader_is_leader = $LEADER (expected 1)"
    exit 1
fi
echo ""

# 3. Heartbeats
echo "3️⃣  Checking heartbeats (< 5s)..."
HEARTBEAT_METRICS=$(curl -s "$API/metrics" 2>/dev/null | grep '^trader_.*heartbeat_seconds' || echo "")
if [ -z "$HEARTBEAT_METRICS" ]; then
    echo "   ⚠️  No heartbeat metrics found (API may not be running)"
    exit 1
fi

BAD=0
while IFS= read -r line; do
    METRIC=$(echo "$line" | awk '{print $1}')
    VALUE=$(echo "$line" | awk '{print $2}')
    # Use awk for comparison (works with floats)
    if awk "BEGIN {exit !($VALUE >= 5)}" 2>/dev/null; then
        echo "   ❌ $METRIC = ${VALUE}s (>= 5s)"
        BAD=1
    else
        echo "   ✅ $METRIC = ${VALUE}s"
    fi
done <<< "$HEARTBEAT_METRICS"

if [ $BAD -eq 1 ]; then
    echo "   ❌ Some heartbeats >= 5s"
    exit 1
fi
echo ""

# 4. OCO orphans
echo "4️⃣  Checking OCO orphans..."
ORPHANS=$(curl -s "$API/metrics" 2>/dev/null | grep '^trader_oco_orphans_total' | awk '{print $2}' || echo "0")
if [ -z "$ORPHANS" ] || [ "$ORPHANS" = "0" ]; then
    echo "   ✅ trader_oco_orphans_total = ${ORPHANS:-0}"
else
    echo "   ❌ trader_oco_orphans_total = $ORPHANS (expected 0)"
    exit 1
fi
echo ""

# 5. WS reconnects (check rate)
echo "5️⃣  Checking WS reconnects..."
RECONNECTS=$(curl -s "$API/metrics" 2>/dev/null | grep '^trader_crypto_ws_reconnects_total' | awk '{print $2}' || echo "0")
if [ -z "$RECONNECTS" ]; then
    RECONNECTS=0
fi
echo "   ℹ️  trader_crypto_ws_reconnects_total = $RECONNECTS"
if [ "$RECONNECTS" -gt 3 ]; then
    echo "   ⚠️  High reconnect count (check if spike in last 10m)"
fi
echo ""

# 6. Flatten duration (if available)
echo "6️⃣  Checking flatten duration..."
FLATTEN_COUNT=$(curl -s "$API/metrics" 2>/dev/null | grep '^trader_crypto_flatten_duration_seconds_count' | awk '{print $2}' || echo "0")
if [ "$FLATTEN_COUNT" != "0" ] && [ -n "$FLATTEN_COUNT" ]; then
    # Calculate p95 from buckets (simplified check)
    FLATTEN_BUCKETS=$(curl -s "$API/metrics" 2>/dev/null | grep 'trader_crypto_flatten_duration_seconds_bucket.*le="2.0"' | awk '{print $2}' || echo "0")
    if [ "$FLATTEN_BUCKETS" != "0" ] && [ -n "$FLATTEN_BUCKETS" ]; then
        echo "   ✅ Flatten duration data available (count: $FLATTEN_COUNT)"
        echo "   ℹ️  Check p95 < 2s in Prometheus/Grafana"
    else
        echo "   ⚠️  Flatten duration may exceed 2s (check buckets)"
    fi
else
    echo "   ℹ️  No flatten duration data yet (will be available after first flatten)"
fi
echo ""

# 7. Binance-specific checks
echo "7️⃣  Checking Binance-specific metrics..."
# Check time skew (should be < 1000ms)
TIME_SKEW=$(curl -s "$API/metrics" 2>/dev/null | grep '^trader_binance_time_skew_ms' | awk '{print $2}' || echo "0")
if [ -n "$TIME_SKEW" ] && [ "$TIME_SKEW" != "0" ]; then
    # Use awk for float comparison
    if awk "BEGIN {exit !($TIME_SKEW > 1000)}" 2>/dev/null; then
        echo "   ⚠️  Time skew = ${TIME_SKEW}ms (high, but OK if < 5000ms)"
    else
        echo "   ✅ Time skew = ${TIME_SKEW}ms"
    fi
else
    echo "   ⚠️  Time skew metric not available (may be OK on first check)"
fi

# Check rate limits (warn if > 900)
USED_WEIGHT=$(curl -s "$API/metrics" 2>/dev/null | grep '^trader_binance_used_weight_1m' | awk '{print $2}' || echo "0")
if [ -n "$USED_WEIGHT" ] && [ "$USED_WEIGHT" != "0" ]; then
    if awk "BEGIN {exit !($USED_WEIGHT > 900)}" 2>/dev/null; then
        echo "   ⚠️  Used weight = ${USED_WEIGHT}/1200 (near cap)"
    else
        echo "   ✅ Used weight = ${USED_WEIGHT}/1200"
    fi
else
    echo "   ⚠️  Weight metric not available (may be OK on first check)"
fi
echo ""

echo "✅ GO/NO-GO Check Complete"
echo ""
echo "If all checks passed, you're clear to proceed with canary launch."
