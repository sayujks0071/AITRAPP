#!/bin/bash
# Setup Log Monitoring - Redirect logs to /tmp/aitrapp.log
# ========================================================

LOG_FILE="/tmp/aitrapp.log"

echo "🔧 Setting up log monitoring to $LOG_FILE"

# Create log file if it doesn't exist
touch "$LOG_FILE"
chmod 666 "$LOG_FILE"

echo "✅ Log file ready: $LOG_FILE"
echo ""
echo "📊 To monitor evaluations, run in a separate terminal:"
echo "   tail -f $LOG_FILE | grep -i 'Evaluating\\|Skipping\\|Entry\\|Regime\\|Attempting'"
echo ""
echo "💡 Note: If the system is already running, logs may be going to stdout."
echo "   Check the terminal where ./go_live.sh was started for real-time logs."




