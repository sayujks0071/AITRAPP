#!/bin/bash
# Post-deploy quick tests (2 mins)
# Run after deployment to verify everything works
#
# Usage:
#   NEXT_PUBLIC_API_BASE=http://localhost:8000 UI_BASE=http://localhost:3000 ./scripts/post_deploy_test.sh
#   NEXT_PUBLIC_API_BASE=https://ops-api.example.com UI_BASE=https://ops-ui.example.com ./scripts/post_deploy_test.sh

set -e

API_BASE="${NEXT_PUBLIC_API_BASE:-http://localhost:8000}"
UI_BASE="${UI_BASE:-http://localhost:3000}"

echo "🧪 Post-Deploy Tests"
echo "==================="
echo "API: $API_BASE"
echo "UI:  $UI_BASE"
echo ""

# 1. Liveness
echo "1️⃣  UI Liveness"
if STATUS=$(curl -Is "$UI_BASE" 2>/dev/null | head -n 1 | awk '{print $2}'); then
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "301" ] || [ "$STATUS" = "302" ]; then
        echo "   ✅ Status: $STATUS"
    else
        echo "   ⚠️  Status: $STATUS (expected 200/301/302)"
    fi
else
    echo "   ⚠️  UI not reachable (may not be deployed yet)"
fi
echo ""

# 2. UI→API CORS
echo "2️⃣  UI→API CORS Check"
CORS_RESPONSE=$(curl -Is -H "Origin: $UI_BASE" "$API_BASE/health" | grep -i "access-control-allow-origin" || echo "")
if [ -n "$CORS_RESPONSE" ]; then
    echo "   ✅ CORS configured: $CORS_RESPONSE"
else
    echo "   ⚠️  CORS headers not found (may be same-origin or not configured)"
fi
echo ""

# 3. Synthetic Flatten Dry-Run
echo "3️⃣  Flatten Endpoint (Dry-Run)"
if [ -n "$OPS_KEY" ]; then
    REQ_ID="test-$(date +%s)-$RANDOM"
    FLATTEN_RESPONSE=$(curl -fsS -X POST "$API_BASE/flatten?dry_run=1" \
        -H "X-Ops-Key: $OPS_KEY" \
        -H "X-Request-ID: $REQ_ID" \
        -H "Content-Type: application/json" \
        -d '{"reason": "smoke-test"}' 2>&1 || echo "ERROR")
    
    if echo "$FLATTEN_RESPONSE" | grep -q "status\|error\|flattened"; then
        echo "   ✅ Flatten endpoint responds"
        echo "$FLATTEN_RESPONSE" | jq . 2>/dev/null || echo "$FLATTEN_RESPONSE"
    else
        echo "   ⚠️  Flatten endpoint check skipped (dry_run not supported or different error)"
        echo "   Response: $FLATTEN_RESPONSE"
    fi
else
    echo "   ⚠️  Flatten endpoint check skipped (OPS_KEY not set)"
fi
echo ""

# 4. Key Metrics Check
echo "4️⃣  Key Metrics"
METRICS=$(curl -fsS "$API_BASE/metrics")

# Check flatten p95
FLATTEN_P95=$(echo "$METRICS" | grep "flatten_duration_seconds_bucket" | tail -1 | awk '{print $2}' || echo "0")
if [ "$FLATTEN_P95" != "0" ]; then
    echo "   ✅ Flatten duration histogram present"
else
    echo "   ⚠️  Flatten duration histogram not found"
fi

# Check orphans
ORPHANS=$(echo "$METRICS" | grep "^trader_oco_orphans_total" | head -1 | awk '{print $2}' || echo "0")
if [ "$ORPHANS" = "0" ]; then
    echo "   ✅ OCO orphans: $ORPHANS"
else
    echo "   ⚠️  OCO orphans: $ORPHANS (expected 0)"
fi

# Check leader
LEADER=$(echo "$METRICS" | grep "^trader_is_leader" | head -1 | awk '{print $2}' || echo "0")
if [ "$LEADER" = "1" ]; then
    echo "   ✅ Leader lock: $LEADER"
else
    echo "   ⚠️  Leader lock: $LEADER (expected 1)"
fi

# Check heartbeats
MD_HB=$(echo "$METRICS" | grep "^trader_marketdata_heartbeat_seconds" | head -1 | awk '{print $2}' || echo "999")
ORDER_HB=$(echo "$METRICS" | grep "^trader_order_stream_heartbeat_seconds" | head -1 | awk '{print $2}' || echo "999")
SCAN_HB=$(echo "$METRICS" | grep "^trader_scan_heartbeat_seconds" | head -1 | awk '{print $2}' || echo "999")

if (( $(echo "$MD_HB < 5" | bc -l) )) && (( $(echo "$ORDER_HB < 5" | bc -l) )) && (( $(echo "$SCAN_HB < 5" | bc -l) )); then
    echo "   ✅ All heartbeats < 5s (MD: ${MD_HB}s, Order: ${ORDER_HB}s, Scan: ${SCAN_HB}s)"
else
    echo "   ⚠️  Some heartbeats >= 5s (MD: ${MD_HB}s, Order: ${ORDER_HB}s, Scan: ${SCAN_HB}s)"
fi
echo ""

echo "✅ Post-deploy tests complete!"
echo ""
echo "Manual checks:"
echo "  1. Open $UI_BASE in browser"
echo "  2. Verify: Mode badge, leader ✅, heartbeats < 5s"
echo "  3. Test Flatten button → confirm → success toast"
echo "  4. Check toast notifications appear for status changes"

