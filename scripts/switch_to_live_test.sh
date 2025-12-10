#!/bin/bash
# Safe LIVE mode switch for testing
# This switches to LIVE mode with conservative canary config

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "════════════════════════════════════════════════════════════════"
echo "   SWITCHING TO LIVE MODE - TESTING"
echo "   Time: $(date +"%Y-%m-%d %H:%M:%S IST")"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if API is running
echo "1. Checking API status..."
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo "   ❌ API is not running!"
    echo "   → Start API first with: make paper (or make live)"
    exit 1
fi

HEALTH=$(curl -s "$API_URL/health")
CURRENT_MODE=$(echo "$HEALTH" | jq -r '.mode // "UNKNOWN"')
echo "   ✅ API is running"
echo "   Current mode: $CURRENT_MODE"
echo ""

# Check current state
echo "2. Current system state..."
STATE=$(curl -s "$API_URL/state")
POSITIONS=$(echo "$STATE" | jq -r '.positions_count // 0')
PAUSED=$(echo "$STATE" | jq -r '.is_paused // false')

if [ "$POSITIONS" != "0" ]; then
    echo "   ⚠️  WARNING: You have $POSITIONS open positions!"
    echo "   → Close all positions before switching to LIVE"
    exit 1
fi

if [ "$PAUSED" = "true" ]; then
    echo "   ⚠️  System is paused"
    echo "   → Unpause first if needed"
fi

echo "   ✅ System ready for mode switch"
echo ""

# Switch to LIVE mode
echo "3. Switching to LIVE mode..."
echo "   ⚠️  This will enable REAL MONEY TRADING!"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/control/mode" \
    -H "Content-Type: application/json" \
    -d '{
        "mode": "LIVE",
        "confirmation": "CONFIRM LIVE TRADING"
    }')

if echo "$RESPONSE" | jq -e '.new_mode == "LIVE"' > /dev/null 2>&1; then
    echo "   ✅ Successfully switched to LIVE mode"
    echo "$RESPONSE" | jq '.'
else
    echo "   ❌ Failed to switch to LIVE mode"
    echo "$RESPONSE" | jq '.' || echo "$RESPONSE"
    exit 1
fi

echo ""

# Verify LIVE mode
echo "4. Verifying LIVE mode..."
sleep 2
NEW_HEALTH=$(curl -s "$API_URL/health")
NEW_MODE=$(echo "$NEW_HEALTH" | jq -r '.mode // "UNKNOWN"')

if [ "$NEW_MODE" = "LIVE" ]; then
    echo "   ✅ Confirmed: System is in LIVE mode"
    echo "   Mode: $NEW_MODE"
    echo "   Status: $(echo "$NEW_HEALTH" | jq -r '.status')"
    echo "   Paused: $(echo "$NEW_HEALTH" | jq -r '.is_paused')"
else
    echo "   ⚠️  Mode verification failed: $NEW_MODE"
fi

echo ""

# Show system state
echo "5. System state in LIVE mode..."
FINAL_STATE=$(curl -s "$API_URL/state")
echo "$FINAL_STATE" | jq '{
    mode: .mode,
    is_paused: .is_paused,
    is_market_open: .is_market_open,
    positions_count: .positions_count,
    trades_today: .trades_today,
    daily_pnl: .daily_pnl,
    marketdata_connected: .marketdata_connected,
    websocket_connected: .websocket_connected
}'

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "   ✅ LIVE MODE ACTIVE"
echo "   ⚠️  REAL MONEY TRADING IS ENABLED"
echo "   📊 Monitor at: $API_URL/state"
echo "   🛑 To stop: curl -X POST $API_URL/api/control/pause"
echo "   🛑 To flatten: curl -X POST $API_URL/api/control/flatten"
echo "════════════════════════════════════════════════════════════════"

