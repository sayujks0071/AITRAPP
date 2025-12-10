#!/bin/bash
# Test R1 routing to A-G strategies during market hours
# Usage: ./scripts/test_r1_routing.sh [NIFTY|BANKNIFTY]

UNDERLYING="${1:-BANKNIFTY}"
API_BASE="${API_BASE:-http://localhost:8000}"

echo "🔍 Testing R1 Routing for $UNDERLYING"
echo "======================================"
echo ""

echo "📊 Current Regime:"
REGIME_CODE=$(curl -s "$API_BASE/metrics" | grep "algo_vol_regime_code{underlying=\"$UNDERLYING\"}" | grep -v "^#" | awk '{print $NF}')
if [ -z "$REGIME_CODE" ]; then
    echo "   ⚠️  No regime code found (R1 may not have run yet)"
else
    case "$REGIME_CODE" in
        0) REGIME="UNKNOWN" ;;
        1) REGIME="LOW_MEAN_REVERT" ;;
        2) REGIME="MEDIUM_TREND" ;;
        3) REGIME="HIGH_EVENT" ;;
        4) REGIME="CHAOTIC" ;;
        *) REGIME="UNKNOWN ($REGIME_CODE)" ;;
    esac
    echo "   ✅ Current regime: $REGIME (code: $REGIME_CODE)"
fi

echo ""
echo "📈 Expected Strategies for Current Regime:"
case "$REGIME_CODE" in
    1)
        echo "   - vscore_credit_spread (iron_condor)"
        echo "   - intraday_short_strangle (fallback)"
        ;;
    2)
        echo "   - drifting_credit_spread (primary)"
        echo "   - index_sniper (secondary)"
        ;;
    3)
        echo "   - kurtosis_straddle (long_straddle)"
        echo "   - stay_flat (fallback)"
        ;;
    4)
        echo "   - stay_flat (no trades)"
        ;;
    *)
        echo "   - Unknown regime, check classification"
        ;;
esac

echo ""
echo "🔍 Checking Signal Counts (last 5 minutes):"
echo "   Strategy signals:"
curl -s "$API_BASE/metrics" | grep "trader_signals_total{strategy=" | grep -E "(vscore_credit_spread|intraday_short_strangle|drifting_credit_spread|index_sniper|kurtosis_straddle)" | while read line; do
    STRATEGY=$(echo "$line" | grep -oP 'strategy="\K[^"]+')
    COUNT=$(echo "$line" | awk '{print $NF}')
    echo "   - $STRATEGY: $COUNT"
done

echo ""
echo "💡 Monitoring Commands:"
echo "   # Watch regime changes:"
echo "   watch -n 5 'curl -s $API_BASE/metrics | grep algo_vol_regime_code{underlying=\"$UNDERLYING\"}'"
echo ""
echo "   # Watch signals by strategy:"
echo "   watch -n 5 'curl -s $API_BASE/metrics | grep trader_signals_total{strategy='"


