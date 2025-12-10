#!/bin/bash
# Live MCX + NSE Monitoring Dashboard

echo "════════════════════════════════════════════════════════════════════"
echo "🌙 MCX + NSE LIVE TRADING MONITOR"
echo "════════════════════════════════════════════════════════════════════"
echo "Time: $(date +'%H:%M:%S IST')"
echo ""

# System status
echo "📊 SYSTEM STATUS:"
PID=$(ps aux | grep "apps.api.main" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "  ✅ Running (PID: $PID)"
else
    echo "  ❌ NOT RUNNING"
    exit 1
fi

# Check recent scans
echo ""
echo "🔄 RECENT ACTIVITY (Last 30 seconds):"
tail -200 logs/api_8000_mcx.log | grep "scan cycle" | tail -5 | while read line; do
    echo "  $line" | jq -r '"  ⚡ Scan: \(.timestamp) | Universe: \(.universe) | Using: \(.using) tokens"' 2>/dev/null || echo "  $line"
done

# Check for signals
echo ""
echo "📡 SIGNALS (Last 5 minutes):"
SIGNALS=$(tail -1000 logs/api_8000_mcx.log | grep -i "signal" | tail -5)
if [ -z "$SIGNALS" ]; then
    echo "  ⏳ No signals yet - strategies evaluating..."
else
    echo "$SIGNALS"
fi

# Check PremiumAdaptiveTrend activity
echo ""
echo "🎯 PREMIUM ADAPTIVE TREND (Last 2 minutes):"
PAT=$(tail -500 logs/api_8000_mcx.log | grep "PremiumAdaptiveTrend" | tail -3)
if [ -z "$PAT" ]; then
    echo "  ⏳ Evaluating..."
else
    echo "$PAT"
fi

# MCX specific
echo ""
echo "🌙 MCX INSTRUMENTS:"
tail -500 logs/api_8000_mcx.log | grep -E "CRUDEOIL|GOLDM|SILVERM" | tail -3 || echo "  ⏳ Monitoring CRUDEOIL, GOLDM futures..."

# Entry window
CURRENT_HOUR=$(date +%H)
CURRENT_MIN=$(date +%M)
echo ""
echo "⏰ TRADING WINDOWS:"
if [ $CURRENT_HOUR -lt 15 ]; then
    echo "  🟢 NSE Entry: OPEN (until 3:00 PM)"
elif [ $CURRENT_HOUR -eq 15 ] && [ $CURRENT_MIN -lt 0 ]; then
    echo "  🟢 NSE Entry: OPEN (closing soon)"
else
    echo "  🔴 NSE Entry: CLOSED"
fi

if [ $CURRENT_HOUR -ge 17 ] && [ $CURRENT_HOUR -lt 23 ]; then
    echo "  🟢 MCX Evening: OPEN (until 11:30 PM)"
elif [ $CURRENT_HOUR -eq 23 ] && [ $CURRENT_MIN -lt 30 ]; then
    echo "  🟡 MCX Evening: OPEN (closing soon)"
else
    echo "  🔴 MCX Evening: CLOSED"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "💡 Watch logs: tail -f logs/api_8000_mcx.log | grep -E 'Signal|PremiumAdaptiveTrend'"
echo "💡 MCX Prices: python3 scripts/check_mcx_now.py"
echo "════════════════════════════════════════════════════════════════════"
