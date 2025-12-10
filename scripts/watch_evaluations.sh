#!/bin/bash
# Watch Strategy Evaluations - See What the System is Thinking
# =============================================================

echo "🔍 Monitoring Strategy Evaluations..."
echo "Press Ctrl+C to stop"
echo ""

# Check multiple log locations
LOG_FILES=(
    "/tmp/aitrapp.log"
    "logs/trading.log"
    "logs/aitrapp_crypto.log"
    "logs/aitrapp.log"
)

FOUND_LOG=""

for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        FOUND_LOG="$log_file"
        echo "✅ Found log file: $log_file"
        echo "📊 Monitoring for: Evaluating, Skipping, Entry, Regime"
        echo ""
        tail -f "$log_file" | grep -i --line-buffered "Evaluating\|Skipping\|Entry\|Regime\|Attempting\|Filter"
        break
    fi
done

if [ -z "$FOUND_LOG" ]; then
    echo "⚠️  No log files found in standard locations"
    echo ""
    echo "💡 Logs may be going to stdout (check terminal where go_live.sh is running)"
    echo ""
    echo "Alternative: Monitor via API:"
    echo "  watch -n 2 'curl -s http://localhost:8000/api/execution/stats | python3 -m json.tool'"
fi




