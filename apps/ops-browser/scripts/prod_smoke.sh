#!/bin/bash
# 60-second production smoke test
# Run this after deploying to verify everything works
#
# Usage:
#   # Local defaults (http://localhost:8000, http://localhost:3000)
#   apps/ops-browser/scripts/prod_smoke.sh
#   make ops-smoke
#
#   # Custom API/UI URLs
#   API_BASE=http://localhost:8000 UI_BASE=http://localhost:3000 apps/ops-browser/scripts/prod_smoke.sh
#   API_BASE=https://ops-api.example.com UI_BASE=https://ops-ui.example.com apps/ops-browser/scripts/prod_smoke.sh
#
#   # Skip UI check (API only)
#   SKIP_UI_CHECK=true apps/ops-browser/scripts/prod_smoke.sh
#   make ops-smoke-no-ui
#
#   # Custom required metrics
#   REQUIRE_METRICS="trader_is_leader trader_marketdata_heartbeat_seconds" apps/ops-browser/scripts/prod_smoke.sh

set -e

API_BASE="${API_BASE:-${NEXT_PUBLIC_API_BASE:-http://localhost:8000}}"
UI_BASE="${UI_BASE:-http://localhost:3000}"
SKIP_UI_CHECK="${SKIP_UI_CHECK:-false}"
# Default required metrics (trader_is_leader is optional - only required if trader is running)
REQUIRE_METRICS="${REQUIRE_METRICS:-trader_marketdata_heartbeat_seconds trader_order_stream_heartbeat_seconds trader_scan_heartbeat_seconds}"
# Optional metrics (warn if missing but don't fail)
OPTIONAL_METRICS="${OPTIONAL_METRICS:-trader_is_leader}"

echo "🧪 Production Smoke Test"
echo "========================"
echo "API: $API_BASE"
echo "UI:  $UI_BASE"
echo ""

# 1. UI Liveness (optional)
if [ "$SKIP_UI_CHECK" != "true" ]; then
    echo "1️⃣  UI Liveness Check"
    if curl -fsSI "$UI_BASE" 2>/dev/null | head -n 1 | grep -q "200\|301\|302"; then
        echo "   ✅ UI is reachable"
    else
        echo "   ⚠️  UI not reachable (skipping - set SKIP_UI_CHECK=true to suppress)"
        echo "   💡 This is OK if UI isn't deployed yet or you're only testing API"
    fi
    echo ""
else
    echo "1️⃣  UI Liveness Check (skipped)"
    echo ""
fi

# 2. API Health
echo "2️⃣  API Health Check"
if ! HEALTH=$(curl -fsS "$API_BASE/health" 2>/dev/null | jq -r '.status // empty'); then
    echo "   ❌ API not reachable at $API_BASE"
    echo "   💡 Make sure the API is running and NEXT_PUBLIC_API_BASE is correct"
    exit 1
fi

if [ "$HEALTH" = "healthy" ]; then
    echo "   ✅ API health check passed"
else
    echo "   ❌ API health check failed: $HEALTH"
    exit 1
fi

# Optional: Check /ready (may fail if trader isn't started)
echo "   Checking /ready endpoint..."
READY_STATUS=$(curl -s "$API_BASE/ready" 2>/dev/null | jq -r '.status // empty' || echo "")
if [ "$READY_STATUS" = "ready" ]; then
    echo "   ✅ API readiness check passed (trader is ready)"
elif [ -n "$READY_STATUS" ]; then
    echo "   ⚠️  API not ready: $READY_STATUS (trader may not be started)"
else
    echo "   ⚠️  /ready endpoint returned error (trader may not be started - this is OK for smoke test)"
fi
echo ""

# 3. API Metrics
echo "3️⃣  API Metrics Check"
if ! METRICS=$(curl -fsS "$API_BASE/metrics" 2>/dev/null); then
    echo "   ❌ Metrics endpoint not reachable"
    exit 1
fi

# Save metrics to temp file for validation
METRICS_FILE=$(mktemp)
echo "$METRICS" > "$METRICS_FILE"

if echo "$METRICS" | grep -q "trader_is_leader\|trader_.*_heartbeat"; then
    echo "   ✅ Metrics endpoint returns Prometheus format"
else
    echo "   ❌ Metrics endpoint format invalid"
    echo "   Sample output:"
    echo "$METRICS" | head -n 5
    rm -f "$METRICS_FILE"
    exit 1
fi

# Validate required metrics
echo "   Checking required metrics..."
MISSING_METRICS=""
for m in $REQUIRE_METRICS; do
    if ! grep -q "^${m}" "$METRICS_FILE"; then
        MISSING_METRICS="${MISSING_METRICS} ${m}"
    fi
done

if [ -n "$MISSING_METRICS" ]; then
    echo "   ❌ Missing required metrics:$MISSING_METRICS"
    echo "   💡 This usually means:"
    echo "      - API is running but trader isn't started"
    echo "      - Metrics haven't been initialized yet"
    echo ""
    echo "   Available trader metrics:"
    grep "^trader_" "$METRICS_FILE" | head -5 | sed 's/^/      /' || echo "      (none found)"
    rm -f "$METRICS_FILE"
    exit 1
fi

echo "   ✅ Required metrics present: $REQUIRE_METRICS"

# Check optional metrics (warn if missing)
if [ -n "$OPTIONAL_METRICS" ]; then
    MISSING_OPTIONAL=""
    for m in $OPTIONAL_METRICS; do
        if ! grep -q "^${m}" "$METRICS_FILE"; then
            MISSING_OPTIONAL="${MISSING_OPTIONAL} ${m}"
        fi
    done
    
    if [ -n "$MISSING_OPTIONAL" ]; then
        echo "   ⚠️  Optional metrics missing:$MISSING_OPTIONAL (trader may not be started)"
    else
        echo "   ✅ Optional metrics present: $OPTIONAL_METRICS"
    fi
fi

rm -f "$METRICS_FILE"
echo ""

# 4. CORS Check
echo "4️⃣  CORS Configuration"
CORS_HEADER=$(curl -fsSI -H "Origin: $UI_BASE" "$API_BASE/health" | grep -i "access-control-allow-origin" || echo "")
if [ -n "$CORS_HEADER" ]; then
    echo "   ✅ CORS headers present: $CORS_HEADER"
else
    echo "   ⚠️  CORS headers not found (may be same-origin)"
fi
echo ""

# 5. Key Metrics Check
echo "5️⃣  Key Metrics Values"
if ! METRICS_TEXT=$(curl -fsS "$API_BASE/metrics" 2>/dev/null); then
    echo "   ❌ Could not fetch metrics"
    exit 1
fi

LEADER=$(echo "$METRICS_TEXT" | grep "^trader_is_leader" | head -1 | awk '{print $2}' || echo "0")
ORPHANS=$(echo "$METRICS_TEXT" | grep "^trader_oco_orphans_total" | head -1 | awk '{print $2}' || echo "0")

if [ "$LEADER" = "1" ]; then
    echo "   ✅ Leader lock: $LEADER"
else
    echo "   ⚠️  Leader lock: $LEADER (expected 1)"
fi

if [ "$ORPHANS" = "0" ]; then
    echo "   ✅ OCO orphans: $ORPHANS"
else
    echo "   ⚠️  OCO orphans: $ORPHANS (expected 0)"
fi
echo ""

# 6. Flatten Endpoint (dry-run if supported)
echo "6️⃣  Flatten Endpoint Check"
if [ -n "$OPS_KEY" ]; then
    REQ_ID="smoke-test-$(date +%s)"
    if FLATTEN_RESPONSE=$(curl -fsS -X POST "$API_BASE/flatten?dry_run=1" \
        -H "X-Ops-Key: $OPS_KEY" \
        -H "X-Request-ID: $REQ_ID" \
        -H "Content-Type: application/json" \
        -d '{"reason": "smoke-test"}' 2>&1); then
        if echo "$FLATTEN_RESPONSE" | grep -q "status\|error\|flattened"; then
            echo "   ✅ Flatten endpoint responds (dry-run)"
        else
            echo "   ⚠️  Flatten endpoint responded but format unexpected"
        fi
    else
        echo "   ⚠️  Flatten endpoint check failed (may not support dry_run or different auth)"
    fi
else
    echo "   ⚠️  Flatten endpoint check skipped (OPS_KEY not set)"
    echo "   💡 Set OPS_KEY env var to test flatten endpoint"
fi
echo ""

echo "✅ Smoke test complete!"
echo ""
echo "Next steps:"
echo "  1. Open $UI_BASE in browser"
echo "  2. Verify: Mode badge, leader ✅, heartbeats < 5s"
echo "  3. Test Flatten button (with confirmation)"
echo "  4. Check toast notifications work"

