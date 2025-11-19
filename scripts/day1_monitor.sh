#!/bin/bash
# Day-1 Live Trading Monitor
# Run this every 15-30 minutes during trading hours
# Usage: bash scripts/day1_monitor.sh

set -e

API_URL="${API_URL:-http://localhost:8000}"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "════════════════════════════════════════════════════════════════"
echo "   DAY-1 LIVE TRADING MONITOR"
echo "   Time: $TIMESTAMP"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Function to colorize output
green() { echo -e "\033[0;32m$1\033[0m"; }
yellow() { echo -e "\033[1;33m$1\033[0m"; }
red() { echo -e "\033[0;31m$1\033[0m"; }
blue() { echo -e "\033[0;34m$1\033[0m"; }

# 1. System Health
echo "$(blue '1. SYSTEM HEALTH')"
HEALTH=$(curl -s "$API_URL/health" 2>/dev/null || echo '{"status":"ERROR"}')
MODE=$(echo "$HEALTH" | jq -r '.mode // "UNKNOWN"')
PAUSED=$(echo "$HEALTH" | jq -r '.is_paused // false')
STATUS=$(echo "$HEALTH" | jq -r '.status // "unknown"')

if [ "$STATUS" = "healthy" ]; then
    echo "   Status: $(green "✓ HEALTHY")"
else
    echo "   Status: $(red "✗ UNHEALTHY")"
fi

echo "   Mode: $MODE"

if [ "$PAUSED" = "false" ]; then
    echo "   Trading: $(green "✓ ACTIVE")"
else
    echo "   Trading: $(yellow "⚠ PAUSED")"
fi
echo ""

# 2. Ready Status (Leader + Heartbeats)
echo "$(blue '2. READY STATUS')"
READY=$(curl -s "$API_URL/ready" 2>/dev/null || echo '{"ready":false}')
IS_READY=$(echo "$READY" | jq -r '.ready // false')
LEADER=$(echo "$READY" | jq -r '.leader // 0')
MD_HB=$(echo "$READY" | jq -r '.marketdata_heartbeat // 9999')
SCAN_HB=$(echo "$READY" | jq -r '.scan_heartbeat // 9999')

if [ "$IS_READY" = "true" ]; then
    echo "   Ready: $(green "✓ YES")"
else
    echo "   Ready: $(red "✗ NO")"
fi

if [ "$LEADER" = "1" ]; then
    echo "   Leader: $(green "✓ YES")"
else
    echo "   Leader: $(red "✗ NO")"
fi

# Check if marketdata heartbeat is fresh (convert to integer comparison)
MD_HB_INT=$(echo "$MD_HB" | cut -d. -f1)
if [ "$MD_HB_INT" -lt 5 ] 2>/dev/null; then
    echo "   Market Data: $(green "✓ FRESH") (${MD_HB}s)"
else
    echo "   Market Data: $(red "✗ STALE") (${MD_HB}s)"
fi

SCAN_HB_INT=$(echo "$SCAN_HB" | cut -d. -f1)
if [ "$SCAN_HB_INT" -lt 5 ] 2>/dev/null; then
    echo "   Scan: $(green "✓ FRESH") (${SCAN_HB}s)"
else
    echo "   Scan: $(yellow "⚠ STALE") (${SCAN_HB}s)"
fi
echo ""

# 3. Risk State
echo "$(blue '3. RISK STATE')"
RISK=$(curl -s "$API_URL/risk" 2>/dev/null || echo '{}')
USED_MARGIN=$(echo "$RISK" | jq -r '.used_margin // 0')
AVAIL_MARGIN=$(echo "$RISK" | jq -r '.available_margin // 1000000')
DAILY_PNL=$(echo "$RISK" | jq -r '.daily_pnl // 0')
DAILY_LOSS_LIMIT=$(echo "$RISK" | jq -r '.daily_loss_limit // -25000')
OPEN_POS=$(echo "$RISK" | jq -r '.open_positions_count // 0')
CAN_TRADE=$(echo "$RISK" | jq -r '.can_take_new_position // false')

# Calculate margin %
if [ "$AVAIL_MARGIN" != "0" ]; then
    TOTAL_MARGIN=$((USED_MARGIN + AVAIL_MARGIN))
    MARGIN_PCT=$(awk "BEGIN {printf \"%.1f\", ($USED_MARGIN / $TOTAL_MARGIN) * 100}")
else
    MARGIN_PCT="0.0"
fi

echo "   Used Margin: ₹$(printf "%'d" "$USED_MARGIN") ($MARGIN_PCT%)"

# Color code margin usage
MARGIN_PCT_INT=$(echo "$MARGIN_PCT" | cut -d. -f1)
if [ "$MARGIN_PCT_INT" -lt 15 ]; then
    echo "   Margin Status: $(green "✓ OK")"
elif [ "$MARGIN_PCT_INT" -lt 30 ]; then
    echo "   Margin Status: $(yellow "⚠ ELEVATED")"
else
    echo "   Margin Status: $(red "✗ HIGH")"
fi

# Daily PnL
DAILY_PNL_INT=$(echo "$DAILY_PNL" | cut -d. -f1)
if [ "$DAILY_PNL_INT" -ge 0 ]; then
    echo "   Daily PnL: $(green "+₹$(printf "%'d" "$DAILY_PNL_INT")")"
elif [ "$DAILY_PNL_INT" -gt -12500 ]; then
    echo "   Daily PnL: $(yellow "₹$(printf "%'d" "$DAILY_PNL_INT")")"
elif [ "$DAILY_PNL_INT" -gt -20000 ]; then
    echo "   Daily PnL: $(yellow "⚠ ₹$(printf "%'d" "$DAILY_PNL_INT")") (approaching soft limit)"
else
    echo "   Daily PnL: $(red "✗ ₹$(printf "%'d" "$DAILY_PNL_INT")") (near hard limit: ₹$DAILY_LOSS_LIMIT)"
fi

echo "   Open Positions: $OPEN_POS / 2"

if [ "$CAN_TRADE" = "true" ]; then
    echo "   Can Trade: $(green "✓ YES")"
else
    echo "   Can Trade: $(red "✗ NO")"
fi
echo ""

# 4. Positions Detail
echo "$(blue '4. POSITIONS')"
POSITIONS=$(curl -s "$API_URL/positions" 2>/dev/null || echo '{"positions":[],"count":0}')
POS_COUNT=$(echo "$POSITIONS" | jq -r '.count // 0')

if [ "$POS_COUNT" -eq 0 ]; then
    echo "   $(green "No open positions (flat)")"
else
    echo "   Count: $POS_COUNT"
    echo ""

    # Parse each position
    echo "$POSITIONS" | jq -r '.positions[] |
        "   Position: \(.position_id // "unknown")\n" +
        "     Strategy: \(.strategy // "unknown")\n" +
        "     Instrument: \(.instrument // "unknown")\n" +
        "     Quantity: \(.quantity // 0)\n" +
        "     Entry: ₹\(.entry_price // 0)\n" +
        "     Current: ₹\(.current_price // 0)\n" +
        "     Unrealized PnL: ₹\(.unrealized_pnl // 0)\n" +
        "     PnL %: \(.pnl_pct // 0)%\n"
    '
fi
echo ""

# 5. Orders (recent)
echo "$(blue '5. ORDERS (TODAY)')"
ORDERS=$(curl -s "$API_URL/orders" 2>/dev/null || echo '{"orders":[],"count":0}')
ORDER_COUNT=$(echo "$ORDERS" | jq -r '.count // 0')

if [ "$ORDER_COUNT" -eq 0 ]; then
    echo "   $(green "No orders today")"
else
    echo "   Count: $ORDER_COUNT"

    # Show last 3 orders
    echo "$ORDERS" | jq -r '.orders[-3:] | .[] |
        "   Order: \(.order_id // "unknown")\n" +
        "     Status: \(.status.value // "unknown")\n" +
        "     Side: \(.side // "unknown")\n" +
        "     Qty: \(.quantity // 0) (filled: \(.filled_quantity // 0))\n"
    ' 2>/dev/null || echo "   (Unable to parse orders)"
fi
echo ""

# 6. Overall Status Summary
echo "$(blue '6. OVERALL STATUS')"

# Calculate overall health score
HEALTHY=0
TOTAL_CHECKS=6

[ "$STATUS" = "healthy" ] && HEALTHY=$((HEALTHY + 1))
[ "$IS_READY" = "true" ] && HEALTHY=$((HEALTHY + 1))
[ "$LEADER" = "1" ] && HEALTHY=$((HEALTHY + 1))
[ "$MD_HB_INT" -lt 5 ] 2>/dev/null && HEALTHY=$((HEALTHY + 1))
[ "$MARGIN_PCT_INT" -lt 30 ] 2>/dev/null && HEALTHY=$((HEALTHY + 1))
[ "$DAILY_PNL_INT" -gt -20000 ] 2>/dev/null && HEALTHY=$((HEALTHY + 1))

if [ "$HEALTHY" -eq "$TOTAL_CHECKS" ]; then
    echo "   $(green "✓ ALL SYSTEMS GREEN")"
    echo "   $(green "   Safe to continue trading")"
elif [ "$HEALTHY" -ge 4 ]; then
    echo "   $(yellow "⚠ MOSTLY HEALTHY")"
    echo "   $(yellow "   Monitor closely, some warnings present")"
else
    echo "   $(red "✗ ISSUES DETECTED")"
    echo "   $(red "   Consider pausing or flattening")"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Optional: Alert if critical issues
if [ "$IS_READY" != "true" ] && [ "$MD_HB_INT" -gt 10 ] 2>/dev/null; then
    echo "$(red '⚠⚠⚠ CRITICAL: System not ready, market data stale')"
    echo "$(red 'ACTION: Do not take new trades until this resolves')"
    echo ""
fi

if [ "$DAILY_PNL_INT" -lt -20000 ] 2>/dev/null; then
    echo "$(red '⚠⚠⚠ WARNING: Daily loss approaching hard limit')"
    echo "$(red 'ACTION: Consider manual flatten if losses continue')"
    echo ""
fi

if [ "$MARGIN_PCT_INT" -gt 30 ] 2>/dev/null; then
    echo "$(yellow '⚠ WARNING: Margin usage high')"
    echo "$(yellow 'ACTION: No new positions until margin frees up')"
    echo ""
fi

exit 0
