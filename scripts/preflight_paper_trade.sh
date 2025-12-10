#!/usr/bin/env bash
# Pre-flight check for live paper trading
# Comprehensive system readiness verification

set -euo pipefail
IFS=$'\n\t'

API="${API:-http://localhost:8000}"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S IST")

echo "=========================================="
echo "🚀 PRE-FLIGHT CHECK - LIVE PAPER TRADE"
echo "=========================================="
echo "Time: $TIMESTAMP"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS_COUNT++)) || true
}

fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL_COUNT++)) || true
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARN_COUNT++)) || true
}

# Check if API is running
echo "1. BACKEND CONNECTIVITY"
echo "----------------------"
if curl -s --max-time 5 "$API/health" >/dev/null 2>&1; then
    pass "API is running and accessible"
else
    fail "API is not accessible at $API"
    echo "   → Start API: cd /Users/mac/CRYPTO/AITRAPP && source venv/bin/activate && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# Get health status
HEALTH=$(curl -s "$API/health" 2>/dev/null || echo '{}')
MODE=$(echo "$HEALTH" | jq -r '.mode // "UNKNOWN"' 2>/dev/null || echo "UNKNOWN")
STATUS=$(echo "$HEALTH" | jq -r '.status // "UNKNOWN"' 2>/dev/null || echo "UNKNOWN")
IS_PAUSED=$(echo "$HEALTH" | jq -r '.is_paused // true' 2>/dev/null || echo "true")

if [[ "$MODE" == "PAPER" || "$MODE" == "LIVE" ]]; then
    pass "Mode: $MODE"
else
    fail "Mode: $MODE (expected PAPER or LIVE)"
fi

if [[ "$STATUS" == "healthy" ]]; then
    pass "Status: $STATUS"
else
    fail "Status: $STATUS (expected healthy)"
fi

if [[ "$IS_PAUSED" == "false" ]]; then
    pass "Trading is NOT paused"
else
    warn "Trading is PAUSED"
fi

echo ""

# Check market data and heartbeats
echo "2. MARKET DATA & HEARTBEATS"
echo "---------------------------"
METRICS=$(curl -s "$API/metrics" 2>/dev/null || echo "")

if [[ -z "$METRICS" ]]; then
    fail "Could not fetch metrics"
else
    LEADER=$(echo "$METRICS" | awk '/^trader_is_leader[^_]/ {print $2; exit}' || echo "0")
    MKT_HB=$(echo "$METRICS" | awk '/^trader_marketdata_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
    ORD_HB=$(echo "$METRICS" | awk '/^trader_order_stream_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
    SCAN_HB=$(echo "$METRICS" | awk '/^trader_scan_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
    
    if [[ "$LEADER" == "1" ]]; then
        pass "Leader lock: $LEADER (active)"
    else
        fail "Leader lock: $LEADER (expected 1)"
    fi
    
    if (( $(echo "$MKT_HB < 5" | bc -l 2>/dev/null || echo 0) )); then
        pass "Market data heartbeat: ${MKT_HB}s (< 5s)"
    else
        fail "Market data heartbeat: ${MKT_HB}s (>= 5s - stale)"
    fi
    
    if (( $(echo "$ORD_HB < 5" | bc -l 2>/dev/null || echo 0) )); then
        pass "Order stream heartbeat: ${ORD_HB}s (< 5s)"
    else
        fail "Order stream heartbeat: ${ORD_HB}s (>= 5s - stale)"
    fi
    
    if (( $(echo "$SCAN_HB < 5" | bc -l 2>/dev/null || echo 0) )); then
        pass "Scan heartbeat: ${SCAN_HB}s (< 5s)"
    else
        fail "Scan heartbeat: ${SCAN_HB}s (>= 5s - stale)"
    fi
fi

echo ""

# Check ready status
echo "3. READY STATUS"
echo "--------------"
READY=$(curl -s "$API/ready" 2>/dev/null || echo '{}')
READY_STATUS=$(echo "$READY" | jq -r '.ready // false' 2>/dev/null || echo "false")

if [[ "$READY_STATUS" == "true" ]]; then
    pass "System is READY for trading"
else
    fail "System is NOT ready (ready=false)"
    echo "$READY" | jq '.' 2>/dev/null || echo "$READY"
fi

echo ""

# Check positions
echo "4. POSITIONS & ORDERS"
echo "---------------------"
POSITIONS=$(curl -s "$API/positions" 2>/dev/null || echo '{}')
POS_COUNT=$(echo "$POSITIONS" | jq -r '.count // length // 0' 2>/dev/null || echo "0")

if [[ "$POS_COUNT" == "0" ]]; then
    pass "Open positions: $POS_COUNT (flat)"
else
    fail "Open positions: $POS_COUNT (expected 0)"
    echo "$POSITIONS" | jq '.' 2>/dev/null || echo "$POSITIONS"
fi

ORDERS=$(curl -s "$API/orders" 2>/dev/null || echo '[]')
ORD_COUNT=$(echo "$ORDERS" | jq -r 'length // 0' 2>/dev/null || echo "0")

if [[ "$ORD_COUNT" == "0" ]]; then
    pass "Pending orders: $ORD_COUNT"
else
    warn "Pending orders: $ORD_COUNT"
    echo "$ORDERS" | jq '.' 2>/dev/null || echo "$ORDERS"
fi

echo ""

# Check risk state
echo "5. RISK STATE"
echo "-------------"
RISK=$(curl -s "$API/risk" 2>/dev/null || echo '{}')
USED_MARGIN=$(echo "$RISK" | jq -r '.used_margin // 0' 2>/dev/null || echo "0")
AVAIL_MARGIN=$(echo "$RISK" | jq -r '.available_margin // 0' 2>/dev/null || echo "0")
NET_LIQUID=$(echo "$RISK" | jq -r '.net_liquid // 0' 2>/dev/null || echo "0")
CAN_TRADE=$(echo "$RISK" | jq -r '.can_take_new_position // false' 2>/dev/null || echo "false")

if (( $(echo "$NET_LIQUID > 0" | bc -l 2>/dev/null || echo 0) )); then
    pass "Net liquid: ₹$(printf "%.2f" "$NET_LIQUID" | sed 's/\B[0-9]\{3\}>/,&/g')"
else
    fail "Net liquid: ₹$NET_LIQUID (expected > 0)"
fi

if (( $(echo "$AVAIL_MARGIN > 0" | bc -l 2>/dev/null || echo 0) )); then
    pass "Available margin: ₹$(printf "%.2f" "$AVAIL_MARGIN" | sed 's/\B[0-9]\{3\}>/,&/g')"
else
    fail "Available margin: ₹$AVAIL_MARGIN (expected > 0)"
fi

if [[ "$CAN_TRADE" == "true" ]]; then
    pass "Can take new positions: YES"
else
    fail "Can take new positions: NO (blocked)"
fi

echo ""

# Check strategies
echo "6. STRATEGIES"
echo "------------"
STRATEGIES=$(curl -s "$API/strategies" 2>/dev/null || echo '[]')
STRAT_COUNT=$(echo "$STRATEGIES" | jq -r 'length // 0' 2>/dev/null || echo "0")

if (( STRAT_COUNT > 0 )); then
    pass "Strategies loaded: $STRAT_COUNT"
    
    # List enabled strategies
    ENABLED=$(echo "$STRATEGIES" | jq -r '.[] | select(.enabled == true) | .name' 2>/dev/null || echo "")
    if [[ -n "$ENABLED" ]]; then
        echo "   Enabled strategies:"
        echo "$ENABLED" | while read -r strat; do
            echo "   - $strat"
        done
    else
        warn "No enabled strategies found"
    fi
else
    fail "No strategies loaded"
fi

echo ""

# Check broker connectivity (Kite)
echo "7. BROKER CONNECTIVITY"
echo "---------------------"
if curl -s "$API/api/portfolio" >/dev/null 2>&1; then
    PORTFOLIO=$(curl -s "$API/api/portfolio" 2>/dev/null || echo '{}')
    if echo "$PORTFOLIO" | jq -e '.net_liquid' >/dev/null 2>&1; then
        pass "Kite connection: Active"
    else
        warn "Kite connection: Response format unexpected"
    fi
else
    fail "Kite connection: Cannot reach portfolio endpoint"
fi

echo ""

# Summary
echo "=========================================="
echo "📊 SUMMARY"
echo "=========================================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo "⚠️  Warnings: $WARN_COUNT"
echo ""

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN}✅ PRE-FLIGHT CHECK PASSED${NC}"
    echo "System is ready for live paper trading"
    exit 0
else
    echo -e "${RED}❌ PRE-FLIGHT CHECK FAILED${NC}"
    echo "Please fix the issues above before trading"
    exit 1
fi
