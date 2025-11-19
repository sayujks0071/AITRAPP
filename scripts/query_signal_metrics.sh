#!/bin/bash
# Query OptionsRanker Signal Generation Metrics
# Shows why signals were rejected and how many passed

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "════════════════════════════════════════════════════════════════"
echo "   OptionsRanker Signal Generation Analysis"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Function to parse Prometheus metrics
parse_metric() {
    local metric_name=$1
    local result=$(curl -s "$API_URL/metrics" 2>/dev/null | grep "^${metric_name}" | grep -v "#")
    echo "$result"
}

# 1. Total Setups Evaluated
echo "📊 SETUPS EVALUATED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SETUPS_RAW=$(parse_metric "options_ranker_setups_evaluated_total")

if [ -z "$SETUPS_RAW" ]; then
    echo "No setups evaluated yet (0)"
else
    echo "$SETUPS_RAW" | while IFS= read -r line; do
        # Extract labels and value
        STRATEGY_TYPE=$(echo "$line" | grep -o 'strategy_type="[^"]*"' | cut -d'"' -f2)
        UNDERLYING=$(echo "$line" | grep -o 'underlying="[^"]*"' | cut -d'"' -f2)
        VALUE=$(echo "$line" | awk '{print $NF}')

        echo "  $UNDERLYING - $STRATEGY_TYPE: $VALUE setups"
    done
fi

echo ""

# 2. Filter Rejections
echo "❌ FILTER REJECTIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REJECTIONS_RAW=$(parse_metric "options_ranker_filter_rejections_total")

if [ -z "$REJECTIONS_RAW" ]; then
    echo "No rejections recorded (all setups passed, or no setups evaluated)"
else
    # Group by filter name
    declare -A filter_counts

    while IFS= read -r line; do
        FILTER=$(echo "$line" | grep -o 'filter_name="[^"]*"' | cut -d'"' -f2)
        UNDERLYING=$(echo "$line" | grep -o 'underlying="[^"]*"' | cut -d'"' -f2)
        VALUE=$(echo "$line" | awk '{print $NF}')

        # Aggregate by filter
        if [ -n "${filter_counts[$FILTER]}" ]; then
            filter_counts[$FILTER]=$((${filter_counts[$FILTER]} + ${VALUE%.*}))
        else
            filter_counts[$FILTER]=${VALUE%.*}
        fi
    done <<< "$REJECTIONS_RAW"

    # Display aggregated results
    for filter in "${!filter_counts[@]}"; do
        count=${filter_counts[$filter]}
        case $filter in
            "iv_percentile")
                echo "  IV Percentile (out of range): $count rejections"
                ;;
            "trend_confirmation")
                echo "  Trend Confirmation (no bias): $count rejections"
                ;;
            "risk_reward")
                echo "  Risk-Reward Ratio (too low): $count rejections"
                ;;
            "liquidity")
                echo "  Liquidity (bid-ask too wide): $count rejections"
                ;;
            "cost")
                echo "  Cost (spread too expensive): $count rejections"
                ;;
            *)
                echo "  $filter: $count rejections"
                ;;
        esac
    done
fi

echo ""

# 3. Signals Approved
echo "✅ SIGNALS APPROVED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

APPROVED_RAW=$(parse_metric "options_ranker_signals_approved_total")

if [ -z "$APPROVED_RAW" ]; then
    echo "No signals approved (0 passed all filters)"
else
    echo "$APPROVED_RAW" | while IFS= read -r line; do
        STRATEGY_TYPE=$(echo "$line" | grep -o 'strategy_type="[^"]*"' | cut -d'"' -f2)
        UNDERLYING=$(echo "$line" | grep -o 'underlying="[^"]*"' | cut -d'"' -f2)
        SPREAD_TYPE=$(echo "$line" | grep -o 'spread_type="[^"]*"' | cut -d'"' -f2)
        VALUE=$(echo "$line" | awk '{print $NF}')

        echo "  $UNDERLYING - $SPREAD_TYPE: $VALUE signals"
    done
fi

echo ""

# 4. Summary
echo "📈 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL_SETUPS=0
TOTAL_REJECTIONS=0
TOTAL_APPROVED=0

if [ -n "$SETUPS_RAW" ]; then
    TOTAL_SETUPS=$(echo "$SETUPS_RAW" | awk '{sum += $NF} END {print int(sum)}')
fi

if [ -n "$REJECTIONS_RAW" ]; then
    TOTAL_REJECTIONS=$(echo "$REJECTIONS_RAW" | awk '{sum += $NF} END {print int(sum)}')
fi

if [ -n "$APPROVED_RAW" ]; then
    TOTAL_APPROVED=$(echo "$APPROVED_RAW" | awk '{sum += $NF} END {print int(sum)}')
fi

echo "Total Setups Evaluated: $TOTAL_SETUPS"
echo "Total Rejected: $TOTAL_REJECTIONS"
echo "Total Approved: $TOTAL_APPROVED"

if [ $TOTAL_SETUPS -gt 0 ]; then
    APPROVAL_RATE=$(awk "BEGIN {printf \"%.1f\", ($TOTAL_APPROVED / $TOTAL_SETUPS) * 100}")
    echo "Approval Rate: ${APPROVAL_RATE}%"
else
    echo "Approval Rate: N/A (no setups evaluated)"
fi

echo ""

# 5. Interpretation
echo "💡 INTERPRETATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $TOTAL_SETUPS -eq 0 ]; then
    echo "⚠️  No setups evaluated"
    echo "   → Strategy didn't run, or market conditions didn't trigger scan"
    echo "   → Check: Is OptionsRanker enabled? Is market data flowing?"
elif [ $TOTAL_APPROVED -eq 0 ]; then
    echo "⚠️  All setups rejected ($TOTAL_SETUPS evaluated)"
    echo "   → Filters are working, but preventing all entries"
    echo "   → Review which filters caused most rejections (above)"

    # Identify top rejection reason
    if [ -n "$REJECTIONS_RAW" ]; then
        TOP_FILTER=$(echo "$REJECTIONS_RAW" | sort -t' ' -k2 -rn | head -1 | grep -o 'filter_name="[^"]*"' | cut -d'"' -f2)
        echo "   → Top blocker: $TOP_FILTER"
        echo ""
        echo "   Possible actions:"
        case $TOP_FILTER in
            "iv_percentile")
                echo "     • Check if market IV is consistently outside 20-80 range"
                echo "     • Consider widening IV range (e.g., 15-85)"
                ;;
            "trend_confirmation")
                echo "     • Check if EMA/Supertrend indicators are working"
                echo "     • Consider softening trend requirements"
                ;;
            "risk_reward")
                echo "     • Check if RR minimum (1.5) is too strict"
                echo "     • Review strike selection logic"
                ;;
        esac
    fi
else
    echo "✅ Healthy signal generation"
    echo "   → $TOTAL_APPROVED signals approved out of $TOTAL_SETUPS evaluated"
    echo "   → Filters are working as designed"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
